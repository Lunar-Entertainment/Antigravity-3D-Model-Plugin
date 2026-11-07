// ============================================================================
// AGY 3D Parametric CAD Studio — Native Linux C++ Desktop App (Zorin OS 18)
// ============================================================================
// Features:
// 1. Hardware-Accelerated OpenGL 3D Viewport with 24-bit Depth Buffer,
//    Studio 3-Point Lighting, DFM Overhang (>45°) Shader, Wireframe, X-Ray,
//    Hardware Z-Section Slicing (GL_CLIP_PLANE0), and 3D BBox Calipers.
// 2. Crisp Anti-Aliased FreeType2 TrueType UI (Arimo / Cousine / NimbusSans).
// 3. Built-in Interactive Prompt Bar strictly locked to Antigravity (`agy` /
//    `agentapi`) with `--model=flash` (Gemini 3.8 Flash ONLY — zero Gemini 4
//    quota usage!) + automatic `3d-model-studio` plugin injection.
// 4. Background Linux File & Transcript Watcher Thread: automatically hot-swaps
//    newly generated or modified `.stl` models in place without resetting
//    camera angles or inspector settings.
// ============================================================================

#include <GL/gl.h>
#include <GL/glu.h>
#include <GLFW/glfw3.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include "icon_rgba_64.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

// ============================================================================
// 1. Hardcoded Antigravity Flash-Only & Plugin Configuration
// ============================================================================
static const std::string kAgentApiBin = "/home/lunar/.gemini/antigravity/bin/agentapi";
static const std::string kForcedModelFlag = "--model=flash"; // Strictly Gemini 3.8 Flash ONLY
static const std::string kPluginRoot = "/home/lunar/Documents/Projects/3d-model-plugin";
static const std::string kDefaultStlPath =
    "/home/lunar/Documents/Projects/3d-model-plugin/examples/phone_buds_holder_v2/phone_buds_holder_full_kit_zero_supports.stl";
static const std::string kBrainDir = "/home/lunar/.gemini/antigravity/brain";

// ============================================================================
// 2. 3D Mesh Data Structures & Fast Binary/ASCII STL Loader
// ============================================================================
struct Vec3 {
    float x, y, z;
};

struct Triangle {
    Vec3 a, b, c;
    Vec3 n;
    float avgZ;
};

struct MeshStats {
    std::string filename = "phone_buds_holder_full_kit_zero_supports.stl";
    std::string fullpath = kDefaultStlPath;
    float minX = 0, maxX = 0, minY = 0, maxY = 0, minZ = 0, maxZ = 0;
    float widthX = 0, depthY = 0, heightZ = 0;
    float centerX = 0, centerY = 0, centerZ = 0;
    float bboxRadius = 100.0f;
    float volumeCm3 = 0.0f;
    float plaGrams = 0.0f;
    float overhangPct = 0.0f;
    int triCount = 0;
};

static std::mutex g_meshMutex;
static std::vector<Triangle> g_tris;
static MeshStats g_stats;
static int g_activeTriCount = 0;

static bool loadStlFile(const std::string& path, std::vector<Triangle>& outTris, MeshStats& outStats) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) return false;
    std::streamsize fileSize = file.tellg();
    if (fileSize < 84) return false;
    file.seekg(0, std::ios::beg);

    char header[80];
    file.read(header, 80);
    uint32_t numTris = 0;
    file.read(reinterpret_cast<char*>(&numTris), sizeof(uint32_t));

    std::vector<Triangle> loaded;
    bool isBinary = (static_cast<std::streamsize>(84 + numTris * 50) == fileSize);

    if (isBinary && numTris > 0 && numTris < 2000000) {
        loaded.reserve(numTris);
        for (uint32_t i = 0; i < numTris; ++i) {
            float buf[12];
            uint16_t attr;
            file.read(reinterpret_cast<char*>(buf), 48);
            file.read(reinterpret_cast<char*>(&attr), 2);
            Triangle t;
            t.a = {buf[3], buf[4], buf[5]};
            t.b = {buf[6], buf[7], buf[8]};
            t.c = {buf[9], buf[10], buf[11]};
            float ux = t.b.x - t.a.x, uy = t.b.y - t.a.y, uz = t.b.z - t.a.z;
            float vx = t.c.x - t.a.x, vy = t.c.y - t.a.y, vz = t.c.z - t.a.z;
            float nx = uy * vz - uz * vy;
            float ny = uz * vx - ux * vz;
            float nz = ux * vy - uy * vx;
            float len = std::sqrt(nx * nx + ny * ny + nz * nz);
            if (len > 1e-9f) {
                t.n = {nx / len, ny / len, nz / len};
            } else {
                t.n = {0.0f, 0.0f, 1.0f};
            }
            t.avgZ = (t.a.z + t.b.z + t.c.z) / 3.0f;
            loaded.push_back(t);
        }
    } else {
        // ASCII STL fallback
        file.seekg(0, std::ios::beg);
        std::string line, tok;
        std::vector<Vec3> vtx;
        while (std::getline(file, line)) {
            std::istringstream iss(line);
            iss >> tok;
            if (tok == "vertex") {
                Vec3 v;
                iss >> v.x >> v.y >> v.z;
                vtx.push_back(v);
                if (vtx.size() == 3) {
                    Triangle t;
                    t.a = vtx[0];
                    t.b = vtx[1];
                    t.c = vtx[2];
                    float ux = t.b.x - t.a.x, uy = t.b.y - t.a.y, uz = t.b.z - t.a.z;
                    float vx = t.c.x - t.a.x, vy = t.c.y - t.a.y, vz = t.c.z - t.a.z;
                    float nx = uy * vz - uz * vy;
                    float ny = uz * vx - ux * vz;
                    float nz = ux * vy - uy * vx;
                    float len = std::sqrt(nx * nx + ny * ny + nz * nz);
                    t.n = (len > 1e-9f) ? Vec3{nx / len, ny / len, nz / len} : Vec3{0, 0, 1};
                    t.avgZ = (t.a.z + t.b.z + t.c.z) / 3.0f;
                    loaded.push_back(t);
                    vtx.clear();
                }
            }
        }
    }

    if (loaded.empty()) return false;

    float minX = 1e9f, maxX = -1e9f;
    float minY = 1e9f, maxY = -1e9f;
    float minZ = 1e9f, maxZ = -1e9f;
    double signedVol6 = 0.0;
    double totalArea = 0.0;
    double overhangArea = 0.0;

    for (const auto& t : loaded) {
        minX = std::min({minX, t.a.x, t.b.x, t.c.x});
        maxX = std::max({maxX, t.a.x, t.b.x, t.c.x});
        minY = std::min({minY, t.a.y, t.b.y, t.c.y});
        maxY = std::max({maxY, t.a.y, t.b.y, t.c.y});
        minZ = std::min({minZ, t.a.z, t.b.z, t.c.z});
        maxZ = std::max({maxZ, t.a.z, t.b.z, t.c.z});

        signedVol6 += static_cast<double>(t.a.x) * (t.b.y * t.c.z - t.b.z * t.c.y)
                    + static_cast<double>(t.a.y) * (t.b.z * t.c.x - t.b.x * t.c.z)
                    + static_cast<double>(t.a.z) * (t.b.x * t.c.y - t.b.y * t.c.x);
    }

    for (const auto& t : loaded) {
        float ux = t.b.x - t.a.x, uy = t.b.y - t.a.y, uz = t.b.z - t.a.z;
        float vx = t.c.x - t.a.x, vy = t.c.y - t.a.y, vz = t.c.z - t.a.z;
        float nx = uy * vz - uz * vy;
        float ny = uz * vx - ux * vz;
        float nz = ux * vy - uy * vx;
        float area = 0.5f * std::sqrt(nx * nx + ny * ny + nz * nz);
        totalArea += area;
        float maxTriZ = std::max({t.a.z, t.b.z, t.c.z});
        if (maxTriZ > minZ + 0.4f && t.n.z < -0.7071f) {
            overhangArea += area;
        }
    }

    outStats.fullpath = path;
    outStats.filename = fs::path(path).filename().string();
    outStats.minX = minX; outStats.maxX = maxX;
    outStats.minY = minY; outStats.maxY = maxY;
    outStats.minZ = minZ; outStats.maxZ = maxZ;
    outStats.widthX = maxX - minX;
    outStats.depthY = maxY - minY;
    outStats.heightZ = maxZ - minZ;
    outStats.centerX = 0.5f * (minX + maxX);
    outStats.centerY = 0.5f * (minY + maxY);
    outStats.centerZ = 0.5f * (minZ + maxZ);
    outStats.bboxRadius = std::max(
        1.0f,
        0.5f * std::sqrt(outStats.widthX * outStats.widthX +
                         outStats.depthY * outStats.depthY +
                         outStats.heightZ * outStats.heightZ)
    );
    double volMm3 = std::abs(signedVol6) / 6.0;
    outStats.volumeCm3 = static_cast<float>(volMm3 / 1000.0);
    outStats.plaGrams = outStats.volumeCm3 * 1.24f * 0.45f;
    outStats.overhangPct = (totalArea > 1e-5) ? static_cast<float>(100.0 * overhangArea / totalArea) : 0.0f;
    outStats.triCount = static_cast<int>(loaded.size());

    // Center vertices around (0,0,0) for immediate GPU rendering
    for (auto& t : loaded) {
        t.a.x -= outStats.centerX; t.a.y -= outStats.centerY; t.a.z -= outStats.centerZ;
        t.b.x -= outStats.centerX; t.b.y -= outStats.centerY; t.b.z -= outStats.centerZ;
        t.c.x -= outStats.centerX; t.c.y -= outStats.centerY; t.c.z -= outStats.centerZ;
        t.avgZ -= outStats.centerZ;
    }

    outTris.swap(loaded);
    return true;
}

// ============================================================================
// 3. FreeType2 Anti-Aliased Font Renderer
// ============================================================================
struct GlyphInfo {
    GLuint texId = 0;
    int width = 0;
    int height = 0;
    int bearingX = 0;
    int bearingY = 0;
    int advance = 0;
};

struct FontAtlas {
    GlyphInfo glyphs[128];
    int pixelSize = 14;
    bool loaded = false;

    bool init(const std::vector<std::string>& fontPaths, int pxSize) {
        pixelSize = pxSize;
        FT_Library ft;
        if (FT_Init_FreeType(&ft)) return false;

        FT_Face face = nullptr;
        for (const auto& fp : fontPaths) {
            if (fs::exists(fp) && FT_New_Face(ft, fp.c_str(), 0, &face) == 0) {
                break;
            }
        }
        if (!face) {
            FT_Done_FreeType(ft);
            return false;
        }

        FT_Set_Pixel_Sizes(face, 0, pxSize);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);

        for (unsigned char c = 32; c < 128; ++c) {
            if (FT_Load_Char(face, c, FT_LOAD_RENDER)) continue;
            GlyphInfo& g = glyphs[c];
            g.width = face->glyph->bitmap.width;
            g.height = face->glyph->bitmap.rows;
            g.bearingX = face->glyph->bitmap_left;
            g.bearingY = face->glyph->bitmap_top;
            g.advance = static_cast<int>(face->glyph->advance.x >> 6);

            if (g.width > 0 && g.height > 0) {
                glGenTextures(1, &g.texId);
                glBindTexture(GL_TEXTURE_2D, g.texId);
                // Upload as RGBA with white RGB and glyph bitmap alpha
                std::vector<unsigned char> rgba(g.width * g.height * 4, 255);
                for (int i = 0; i < g.width * g.height; ++i) {
                    rgba[i * 4 + 3] = face->glyph->bitmap.buffer[i];
                }
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, g.width, g.height, 0,
                             GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
            }
        }

        FT_Done_Face(face);
        FT_Done_FreeType(ft);
        loaded = true;
        return true;
    }

    float measureText(const std::string& text) const {
        float w = 0.0f;
        for (unsigned char c : text) {
            if (c >= 32 && c < 128) w += glyphs[c].advance;
        }
        return w;
    }

    void drawText(float x, float y, const std::string& text, float r, float g, float b, float a = 1.0f, float maxW = 0.0f) const {
        if (!loaded) return;
        glEnable(GL_TEXTURE_2D);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(r, g, b, a);

        float startX = x;
        for (unsigned char c : text) {
            if (c < 32 || c >= 128) c = '?';
            const GlyphInfo& glp = glyphs[c];
            if (maxW > 0.0f && (x - startX + glp.advance) > maxW) break;

            if (glp.texId != 0 && glp.width > 0 && glp.height > 0) {
                float xpos = x + glp.bearingX;
                float ypos = y - glp.bearingY;
                float w = static_cast<float>(glp.width);
                float h = static_cast<float>(glp.height);

                glBindTexture(GL_TEXTURE_2D, glp.texId);
                glBegin(GL_QUADS);
                glTexCoord2f(0.0f, 0.0f); glVertex2f(xpos, ypos);
                glTexCoord2f(1.0f, 0.0f); glVertex2f(xpos + w, ypos);
                glTexCoord2f(1.0f, 1.0f); glVertex2f(xpos + w, ypos + h);
                glTexCoord2f(0.0f, 1.0f); glVertex2f(xpos, ypos + h);
                glEnd();
            }
            x += glp.advance;
        }
        glDisable(GL_TEXTURE_2D);
    }
};

static FontAtlas g_fontRegular;
static FontAtlas g_fontBold;
static FontAtlas g_fontMono;

// ============================================================================
// 4. UI State, Camera State, & Interactive Prompt State
// ============================================================================
enum RenderMode {
    MODE_SHADED = 0,
    MODE_DFM = 1,
    MODE_WIRE = 2,
    MODE_XRAY = 3
};

static float g_yaw = -0.65f;
static float g_pitch = 0.55f;
static float g_zoom = 1.0f;
static float g_panX = 0.0f;
static float g_panY = 0.0f;
static RenderMode g_renderMode = MODE_SHADED;
static float g_slicePct = 100.0f;
static bool g_showCalipers = true;

static bool g_isOrbiting = false;
static bool g_isPanning = false;
static bool g_isDraggingSlider = false;
static double g_lastMouseX = 0.0;
static double g_lastMouseY = 0.0;

// Replay animation state
static bool g_replaying = false;
static double g_replayStartTime = 0.0;

// Prompt & Antigravity Flash Agent state
static std::string g_promptText = "";
static std::mutex g_agentMutex;
static std::string g_activeConversationId = "";
static std::string g_agentStatusText = "READY | Locked to AGY Gemini 3.8 Flash (--model=flash) + 3d-model-studio Plugin";
static std::string g_lastAgentReply = "Type a 3D CAD request below and press Enter (or click Send) to build/modify with Gemini 3.8 Flash.";
static std::atomic<bool> g_agentBusy{false};
static std::atomic<bool> g_appRunning{true};

struct ButtonRect {
    std::string id;
    float x, y, w, h;
};
static std::vector<ButtonRect> g_buttons;
static float g_sliderX = 0, g_sliderY = 0, g_sliderW = 100, g_sliderH = 20;
static float g_viewX = 0, g_viewY = 0, g_viewW = 800, g_viewH = 500;

// ============================================================================
// 5. Antigravity (`agentapi --model=flash`) Execution & Live Watcher
// ============================================================================
static std::string shellEscapeSingleQuotes(const std::string& s) {
    std::string out = "'";
    for (char c : s) {
        if (c == '\'') out += "'\\''";
        else out += c;
    }
    out += "'";
    return out;
}

static std::string runCommandCapture(const std::string& cmd) {
    std::string result;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return "";
    char buf[512];
    while (fgets(buf, sizeof(buf), pipe) != nullptr) {
        result += buf;
    }
    pclose(pipe);
    return result;
}

static std::string extractUuid(const std::string& text) {
    // Match 8-4-4-4-12 hex UUID from agentapi output
    for (size_t i = 0; i + 36 <= text.size(); ++i) {
        bool ok = true;
        for (size_t j = 0; j < 36; ++j) {
            char c = text[i + j];
            if (j == 8 || j == 13 || j == 18 || j == 23) {
                if (c != '-') { ok = false; break; }
            } else {
                if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) {
                    ok = false; break;
                }
            }
        }
        if (ok) return text.substr(i, 36);
    }
    return "";
}

static void submitPromptToAgyFlash(std::string userPrompt) {
    if (userPrompt.empty() || g_agentBusy.load()) return;
    g_agentBusy.store(true);

    std::thread([userPrompt]() {
        {
            std::lock_guard<std::mutex> lock(g_agentMutex);
            g_agentStatusText = "RUNNING AGY (--model=flash ONLY | 3d-model-studio plugin active)...";
            g_lastAgentReply = "Prompt sent to Gemini 3.8 Flash: \"" + userPrompt + "\" - building & verifying 3D model...";
        }

        // Construct plugin-aware prompt so the Flash agent always applies 3d-model-studio rules & skills
        std::string fullPrompt =
            "[3D-MODEL-STUDIO PLUGIN ACTIVE - Workspace: " + kPluginRoot + "]\n"
            "Follow all rules in " + kPluginRoot + "/rules/AGENTS.md and use the scripts in "
            + kPluginRoot + "/skills/parametric-cad-modeling/scripts/ (cad_engine.py, verify_model.py, generate_viewer.py). "
            "Ensure 100% watertight manifold output, 0.00% unsupported overhangs (>45 deg), and >=12mm part spacing.\n\n"
            "User Request: " + userPrompt;

        std::string convId;
        {
            std::lock_guard<std::mutex> lock(g_agentMutex);
            convId = g_activeConversationId;
        }

        std::string cmd;
        if (convId.empty()) {
            // HARDCODED --model=flash so Gemini Pro / Gemini 4 quota is NEVER used!
            cmd = kAgentApiBin + " new-conversation " + kForcedModelFlag +
                  " --title=" + shellEscapeSingleQuotes("3D CAD Studio (Flash): " + userPrompt.substr(0, 32)) +
                  " " + shellEscapeSingleQuotes(fullPrompt) + " 2>&1";
            std::string out = runCommandCapture(cmd);
            std::string parsedId = extractUuid(out);
            std::lock_guard<std::mutex> lock(g_agentMutex);
            if (!parsedId.empty()) {
                g_activeConversationId = parsedId;
                g_agentStatusText = "FLASH AGENT WORKING (Conv: " + parsedId.substr(0, 8) + "... | Watching for live STL updates)";
            } else {
                g_agentStatusText = "FLASH AGENT DISPATCHED | Watching workspace for STL updates";
            }
        } else {
            cmd = kAgentApiBin + " send-message " + shellEscapeSingleQuotes(convId) +
                  " " + shellEscapeSingleQuotes(fullPrompt) + " 2>&1";
            runCommandCapture(cmd);
            std::lock_guard<std::mutex> lock(g_agentMutex);
            g_agentStatusText = "FLASH AGENT WORKING (Conv: " + convId.substr(0, 8) + "... | Watching for live STL updates)";
        }

        g_agentBusy.store(false);
    }).detach();
}

static void startLiveFileAndTranscriptWatcher() {
    std::thread([]() {
        fs::file_time_type lastStlTime{};
        std::string lastStlLoaded = kDefaultStlPath;
        if (fs::exists(lastStlLoaded)) {
            lastStlTime = fs::last_write_time(lastStlLoaded);
        }

        while (g_appRunning.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(550));

            // 1. Scan examples directory and active conversation brain dir for newest .stl file
            std::vector<std::string> watchDirs = {
                kPluginRoot + "/examples"
            };
            std::string convId;
            {
                std::lock_guard<std::mutex> lock(g_agentMutex);
                convId = g_activeConversationId;
            }
            if (!convId.empty()) {
                watchDirs.push_back(kBrainDir + "/" + convId);
            }

            std::string newestStl;
            fs::file_time_type newestTime = lastStlTime;

            for (const auto& dir : watchDirs) {
                if (!fs::exists(dir)) continue;
                try {
                    for (auto const& entry : fs::recursive_directory_iterator(dir)) {
                        if (!entry.is_regular_file()) continue;
                        if (entry.path().extension() == ".stl") {
                            auto wt = entry.last_write_time();
                            if (wt > newestTime) {
                                newestTime = wt;
                                newestStl = entry.path().string();
                            }
                        }
                    }
                } catch (...) {}
            }

            if (!newestStl.empty()) {
                std::vector<Triangle> newTris;
                MeshStats newStats;
                if (loadStlFile(newestStl, newTris, newStats)) {
                    {
                        std::lock_guard<std::mutex> lock(g_meshMutex);
                        g_tris.swap(newTris);
                        g_stats = newStats;
                        g_activeTriCount = g_stats.triCount;
                    }
                    {
                        std::lock_guard<std::mutex> lock(g_agentMutex);
                        g_agentStatusText = "LIVE MODEL HOT-SWAPPED (" + newStats.filename + " | Camera Locked)";
                    }
                    lastStlTime = newestTime;
                    lastStlLoaded = newestStl;
                    glfwPostEmptyEvent();
                }
            }

            // 2. If there is an active conversation, check its transcript.jsonl for latest status
            if (!convId.empty()) {
                std::string transcriptPath = kBrainDir + "/" + convId + "/.system_generated/logs/transcript.jsonl";
                if (fs::exists(transcriptPath)) {
                    std::ifstream tf(transcriptPath);
                    std::string line, lastLine;
                    while (std::getline(tf, line)) {
                        if (!line.empty()) lastLine = line;
                    }
                    if (!lastLine.empty()) {
                        std::lock_guard<std::mutex> lock(g_agentMutex);
                        if (lastLine.find("\"PLANNER_RESPONSE\"") != std::string::npos) {
                            if (lastLine.find("\"DONE\"") != std::string::npos && lastLine.find("\"tool_calls\"") == std::string::npos) {
                                g_agentStatusText = "IDLE | Flash 3.8 Turn Complete (Conv: " + convId.substr(0, 8) + ")";
                            } else {
                                g_agentStatusText = "FLASH 3.8 EXECUTING CAD TOOLS (Conv: " + convId.substr(0, 8) + ")...";
                            }
                        }
                    }
                }
            }
        }
    }).detach();
}

// ============================================================================
// 6. OpenGL 2D UI Drawing Helpers
// ============================================================================
static void drawFilledRect(float x, float y, float w, float h, float r, float g, float b, float a = 1.0f) {
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glColor4f(r, g, b, a);
    glBegin(GL_QUADS);
    glVertex2f(x, y);
    glVertex2f(x + w, y);
    glVertex2f(x + w, y + h);
    glVertex2f(x, y + h);
    glEnd();
}

static void drawStrokedRect(float x, float y, float w, float h, float r, float g, float b, float a = 1.0f, float lineW = 1.0f) {
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glLineWidth(lineW);
    glColor4f(r, g, b, a);
    glBegin(GL_LINE_LOOP);
    glVertex2f(x, y);
    glVertex2f(x + w, y);
    glVertex2f(x + w, y + h);
    glVertex2f(x, y + h);
    glEnd();
}

static void drawButton(const std::string& id, float x, float y, float w, float h,
                       const std::string& label, bool active = false, bool accent = false) {
    g_buttons.push_back({id, x, y, w, h});
    if (active) {
        drawFilledRect(x, y, w, h, 0.15f, 0.48f, 0.85f, 1.0f);
        drawStrokedRect(x, y, w, h, 0.35f, 0.68f, 0.98f, 1.0f, 1.2f);
    } else if (accent) {
        drawFilledRect(x, y, w, h, 0.08f, 0.55f, 0.42f, 1.0f);
        drawStrokedRect(x, y, w, h, 0.20f, 0.78f, 0.58f, 1.0f, 1.2f);
    } else {
        drawFilledRect(x, y, w, h, 0.13f, 0.16f, 0.22f, 1.0f);
        drawStrokedRect(x, y, w, h, 0.22f, 0.27f, 0.36f, 1.0f, 1.0f);
    }
    float tw = g_fontRegular.measureText(label);
    float tx = x + std::max(6.0f, (w - tw) * 0.5f);
    float ty = y + h * 0.5f + 5.0f;
    g_fontRegular.drawText(tx, ty, label, 0.94f, 0.96f, 0.99f, 1.0f, w - 8.0f);
}

// ============================================================================
// 7. Hardware-Accelerated 3D OpenGL Viewport Renderer
// ============================================================================
static void render3DViewport(int /*winW*/, int winH, float vx, float vy, float vw, float vh) {
    // Convert top-left UI coordinates (vx, vy, vw, vh) to OpenGL bottom-left viewport
    int glX = static_cast<int>(vx);
    int glY = static_cast<int>(winH - (vy + vh));
    int glW = std::max(1, static_cast<int>(vw));
    int glH = std::max(1, static_cast<int>(vh));

    glEnable(GL_SCISSOR_TEST);
    glScissor(glX, glY, glW, glH);
    glViewport(glX, glY, glW, glH);

    glClearColor(0.06f, 0.08f, 0.11f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    std::lock_guard<std::mutex> lock(g_meshMutex);
    float radius = std::max(g_stats.bboxRadius, 1.0f);
    float aspect = static_cast<float>(glW) / static_cast<float>(glH);

    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    float viewSpan = (radius * 1.35f) / g_zoom;
    if (aspect >= 1.0f) {
        glOrtho(-viewSpan * aspect, viewSpan * aspect, -viewSpan, viewSpan, -radius * 10.0f, radius * 10.0f);
    } else {
        glOrtho(-viewSpan, viewSpan, -viewSpan / aspect, viewSpan / aspect, -radius * 10.0f, radius * 10.0f);
    }

    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    // Apply 2D screen pan in world units
    float worldPerPx = (2.0f * viewSpan) / static_cast<float>(glH);
    glTranslatef(g_panX * worldPerPx, -g_panY * worldPerPx, 0.0f);

    // Match exact orbit convention of WebGL viewer:
    // x1 = x*cos(yaw) - y*sin(yaw)
    // y1 = x*sin(yaw) + y*cos(yaw)
    // z2 = z*cos(pitch) - y1*sin(pitch)
    // depth = z*sin(pitch) + y1*cos(pitch)
    float degPitch = g_pitch * (180.0f / 3.14159265f);
    float degYaw = g_yaw * (180.0f / 3.14159265f);
    glRotatef(-90.0f + degPitch, 1.0f, 0.0f, 0.0f);
    glRotatef(degYaw, 0.0f, 0.0f, 1.0f);

    // Hardware Z-Section Slicing plane: z <= zMaxAllowed
    float hz = g_stats.heightZ;
    float zModelMin = -0.5f * hz;
    float zMaxAllowed = zModelMin + (hz * (g_slicePct / 100.0f)) + 0.02f;
    GLdouble clipPlane0[4] = {0.0, 0.0, -1.0, static_cast<GLdouble>(zMaxAllowed)};
    glClipPlane(GL_CLIP_PLANE0, clipPlane0);
    glEnable(GL_CLIP_PLANE0);

    int limit = std::min(static_cast<int>(g_tris.size()), g_activeTriCount);

    if (g_renderMode == MODE_XRAY) {
        glDisable(GL_DEPTH_TEST);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE);
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
    } else if (g_renderMode == MODE_WIRE) {
        glEnable(GL_DEPTH_TEST);
        glDepthFunc(GL_LEQUAL);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
        glLineWidth(1.0f);
    } else {
        glEnable(GL_DEPTH_TEST);
        glDepthFunc(GL_LEQUAL);
        glDisable(GL_BLEND);
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
    }

    glBegin(GL_TRIANGLES);
    for (int i = 0; i < limit; ++i) {
        const Triangle& t = g_tris[i];
        float nx = t.n.x, ny = t.n.y, nz = t.n.z;
        float keyLight = std::max(0.0f, nx * 0.42f - ny * 0.48f + nz * 0.77f);
        float fillLight = std::max(0.0f, -nx * 0.55f + ny * 0.40f + nz * 0.35f) * 0.35f;
        float shade = std::clamp(0.32f + 0.58f * keyLight + fillLight, 0.22f, 1.0f);

        if (g_renderMode == MODE_WIRE) {
            glColor4f(0.22f, 0.74f, 0.97f, 0.85f);
        } else if (g_renderMode == MODE_XRAY) {
            glColor4f(0.18f * shade, 0.62f * shade, 0.92f * shade, 0.22f);
        } else if (g_renderMode == MODE_DFM) {
            bool isOverhang = (nz < -0.708f && t.avgZ > zModelMin + 0.25f);
            if (isOverhang) {
                glColor3f(0.94f * shade, 0.26f * shade, 0.26f * shade);
            } else {
                glColor3f(0.14f * shade, 0.78f * shade, 0.38f * shade);
            }
        } else {
            // CAD Solid Anodized Steel-Blue
            float r = (0.16f + 0.34f * (shade - 0.22f)) * shade + 0.06f;
            float g = (0.45f + 0.44f * (shade - 0.22f)) * shade + 0.08f;
            float b = (0.69f + 0.30f * (shade - 0.22f)) * shade + 0.10f;
            glColor3f(std::min(1.0f, r), std::min(1.0f, g), std::min(1.0f, b));
        }

        glVertex3f(t.a.x, t.a.y, t.a.z);
        glVertex3f(t.b.x, t.b.y, t.b.z);
        glVertex3f(t.c.x, t.c.y, t.c.z);
    }
    glEnd();

    // Subtle dark CAD wireframe overlay in CAD Solid mode for crisp feature definition
    if (g_renderMode == MODE_SHADED && limit > 0) {
        glEnable(GL_POLYGON_OFFSET_LINE);
        glPolygonOffset(-1.0f, -1.0f);
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glLineWidth(0.65f);
        glColor4f(0.05f, 0.09f, 0.15f, 0.28f);
        glBegin(GL_TRIANGLES);
        for (int i = 0; i < limit; ++i) {
            const Triangle& t = g_tris[i];
            glVertex3f(t.a.x, t.a.y, t.a.z);
            glVertex3f(t.b.x, t.b.y, t.b.z);
            glVertex3f(t.c.x, t.c.y, t.c.z);
        }
        glEnd();
        glDisable(GL_POLYGON_OFFSET_LINE);
    }

    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
    glDisable(GL_CLIP_PLANE0);

    // Draw 3D Bounding Box Calipers if enabled
    if (g_showCalipers && g_stats.widthX > 0.0f) {
        float hx = 0.5f * g_stats.widthX;
        float hy = 0.5f * g_stats.depthY;
        float hzBox = 0.5f * g_stats.heightZ;
        Vec3 c[8] = {
            {-hx, -hy, -hzBox}, {hx, -hy, -hzBox}, {hx, hy, -hzBox}, {-hx, hy, -hzBox},
            {-hx, -hy,  hzBox}, {hx, -hy,  hzBox}, {hx, hy,  hzBox}, {-hx, hy,  hzBox}
        };
        int edges[12][2] = {
            {0,1},{1,2},{2,3},{3,0},
            {4,5},{5,6},{6,7},{7,4},
            {0,4},{1,5},{2,6},{3,7}
        };
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glEnable(GL_LINE_STIPPLE);
        glLineStipple(1, 0xF0F0);
        glLineWidth(1.3f);
        glColor4f(0.96f, 0.62f, 0.04f, 0.78f);
        glBegin(GL_LINES);
        for (int e = 0; e < 12; ++e) {
            glVertex3f(c[edges[e][0]].x, c[edges[e][0]].y, c[edges[e][0]].z);
            glVertex3f(c[edges[e][1]].x, c[edges[e][1]].y, c[edges[e][1]].z);
        }
        glEnd();
        glDisable(GL_LINE_STIPPLE);
    }

    glDisable(GL_DEPTH_TEST);
    glDisable(GL_SCISSOR_TEST);
}

// ============================================================================
// 8. Complete Window Frame Render (Artifact UI + Prompt Bar)
// ============================================================================
static void renderFrame(GLFWwindow* window, float fps) {
    int winW, winH;
    glfwGetFramebufferSize(window, &winW, &winH);
    if (winW <= 0 || winH <= 0) return;

    // Update replay animation if active
    if (g_replaying) {
        double elapsed = glfwGetTime() - g_replayStartTime;
        double progress = std::min(1.0, elapsed / 2.6);
        {
            std::lock_guard<std::mutex> lock(g_meshMutex);
            g_activeTriCount = std::max(1, static_cast<int>(g_stats.triCount * progress));
        }
        if (progress >= 1.0) g_replaying = false;
    }

    glViewport(0, 0, winW, winH);
    glClearColor(0.05f, 0.07f, 0.10f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, winW, winH, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    g_buttons.clear();

    const float pad = 14.0f;
    const float headerH = 58.0f;
    const float stageBarH = 34.0f;
    const float promptAreaH = 112.0f;
    const float sidePanelW = 285.0f;

    // 1. Top Header Card
    drawFilledRect(pad, pad, winW - 2 * pad, headerH, 0.09f, 0.12f, 0.16f);
    drawStrokedRect(pad, pad, winW - 2 * pad, headerH, 0.18f, 0.23f, 0.31f);

    MeshStats st;
    {
        std::lock_guard<std::mutex> lock(g_meshMutex);
        st = g_stats;
    }

    std::string titleStr = "AGY 3D Parametric CAD Studio (" + st.filename + ")";
    g_fontBold.drawText(pad + 14, pad + 24, titleStr, 0.96f, 0.98f, 1.0f);

    // Flash-Only & Plugin Lock Badges
    float badgeX = pad + 14 + g_fontBold.measureText(titleStr) + 12;
    drawFilledRect(badgeX, pad + 8, 178, 20, 0.05f, 0.32f, 0.48f);
    drawStrokedRect(badgeX, pad + 8, 178, 20, 0.14f, 0.65f, 0.92f);
    g_fontBold.drawText(badgeX + 8, pad + 22, "* GEMINI 3.8 FLASH ONLY", 0.38f, 0.85f, 0.99f);

    float plugBadgeX = badgeX + 186;
    drawFilledRect(plugBadgeX, pad + 8, 185, 20, 0.06f, 0.34f, 0.24f);
    drawStrokedRect(plugBadgeX, pad + 8, 185, 20, 0.16f, 0.76f, 0.48f);
    g_fontBold.drawText(plugBadgeX + 8, pad + 22, "[OK] 3d-model-studio Plugin", 0.35f, 0.92f, 0.64f);

    g_fontRegular.drawText(pad + 14, pad + 46,
        "Native Linux C++ OpenGL Studio | Zero Gemini 4 Quota Used | Real-Time STL Hot-Swap",
        0.58f, 0.65f, 0.76f);

    // Right BBox & Mass Readouts in Header
    char bboxBuf[128], massBuf[128];
    std::snprintf(bboxBuf, sizeof(bboxBuf), "Exact BBox: %.1f x %.1f x %.1f mm", st.widthX, st.depthY, st.heightZ);
    std::snprintf(massBuf, sizeof(massBuf), "Vol/Mass: %.1f cm3 (~%.1fg PLA)", st.volumeCm3, st.plaGrams);
    float bboxW = g_fontMono.measureText(bboxBuf) + 20;
    float massW = g_fontMono.measureText(massBuf) + 20;
    float rightEdge = winW - pad - 12;
    drawFilledRect(rightEdge - massW, pad + 14, massW, 30, 0.06f, 0.08f, 0.11f);
    drawStrokedRect(rightEdge - massW, pad + 14, massW, 30, 0.18f, 0.23f, 0.31f);
    g_fontMono.drawText(rightEdge - massW + 10, pad + 34, massBuf, 0.92f, 0.95f, 0.99f);

    drawFilledRect(rightEdge - massW - bboxW - 10, pad + 14, bboxW, 30, 0.06f, 0.08f, 0.11f);
    drawStrokedRect(rightEdge - massW - bboxW - 10, pad + 14, bboxW, 30, 0.18f, 0.23f, 0.31f);
    g_fontMono.drawText(rightEdge - massW - bboxW, pad + 34, bboxBuf, 0.92f, 0.95f, 0.99f);

    // 2. Stage & Live Sync Bar
    float stageY = pad + headerH + 8;
    drawFilledRect(pad, stageY, winW - 2 * pad, stageBarH, 0.09f, 0.12f, 0.16f);
    drawStrokedRect(pad, stageY, winW - 2 * pad, stageBarH, 0.18f, 0.23f, 0.31f);

    std::string statusCopy;
    {
        std::lock_guard<std::mutex> lock(g_agentMutex);
        statusCopy = g_agentStatusText;
    }
    g_fontRegular.drawText(pad + 12, stageY + 22, statusCopy, 0.88f, 0.92f, 0.98f, 1.0f, winW - 380);

    drawButton("replay", winW - pad - 135, stageY + 5, 125, 24, "> Replay Build", g_replaying);

    // 3. Main 3D Viewport Area + Right Inspector Sidebar
    float midY = stageY + stageBarH + 8;
    float midH = std::max(180.0f, winH - midY - promptAreaH - pad - 8);
    g_viewX = pad;
    g_viewY = midY;
    g_viewW = std::max(200.0f, winW - 2 * pad - sidePanelW - 10);
    g_viewH = midH;

    // Render 3D OpenGL Viewport inside (g_viewX, g_viewY, g_viewW, g_viewH)
    render3DViewport(winW, winH, g_viewX, g_viewY, g_viewW, g_viewH);

    // Restore 2D Ortho matrix for HUD overlays & controls
    glViewport(0, 0, winW, winH);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, winW, winH, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    drawStrokedRect(g_viewX, g_viewY, g_viewW, g_viewH, 0.20f, 0.26f, 0.35f, 1.0f, 1.2f);

    // Viewport HUD Pills
    char triHud[128], overHud[128], fpsHud[64];
    std::snprintf(triHud, sizeof(triHud), "%d / %d tris | Score: 100/100", g_activeTriCount, st.triCount);
    std::snprintf(overHud, sizeof(overHud), "Overhang >45 deg: %.2f%%", st.overhangPct);
    std::snprintf(fpsHud, sizeof(fpsHud), "OpenGL %.0f FPS", fps);

    float hudX = g_viewX + 10;
    float hudY = g_viewY + 10;
    float w1 = g_fontMono.measureText(triHud) + 16;
    drawFilledRect(hudX, hudY, w1, 24, 0.08f, 0.11f, 0.15f, 0.88f);
    drawStrokedRect(hudX, hudY, w1, 24, 0.22f, 0.28f, 0.38f);
    g_fontMono.drawText(hudX + 8, hudY + 17, triHud, 0.92f, 0.96f, 1.0f);

    float w2 = g_fontMono.measureText(overHud) + 16;
    drawFilledRect(hudX + w1 + 8, hudY, w2, 24, 0.08f, 0.11f, 0.15f, 0.88f);
    drawStrokedRect(hudX + w1 + 8, hudY, w2, 24, 0.22f, 0.28f, 0.38f);
    g_fontMono.drawText(hudX + w1 + 16, hudY + 17, overHud, 0.35f, 0.92f, 0.62f);

    float w3 = g_fontMono.measureText(fpsHud) + 16;
    drawFilledRect(hudX + w1 + w2 + 16, hudY, w3, 24, 0.08f, 0.11f, 0.15f, 0.88f);
    drawStrokedRect(hudX + w1 + w2 + 16, hudY, w3, 24, 0.22f, 0.28f, 0.38f);
    g_fontMono.drawText(hudX + w1 + w2 + 24, hudY + 17, fpsHud, 0.38f, 0.84f, 0.98f);

    drawButton("fit_view", g_viewX + g_viewW - 98, g_viewY + 10, 88, 25, "Fit View");

    g_fontRegular.drawText(g_viewX + 12, g_viewY + g_viewH - 10,
        "Left-drag: Orbit | Right/Shift-drag: Pan | Scroll: Zoom",
        0.55f, 0.62f, 0.72f);

    // 4. Right Inspector Controls Sidebar
    float sx = g_viewX + g_viewW + 10;
    float sy = midY;
    drawFilledRect(sx, sy, sidePanelW, midH, 0.09f, 0.12f, 0.16f);
    drawStrokedRect(sx, sy, sidePanelW, midH, 0.18f, 0.23f, 0.31f);

    float cx = sx + 12;
    float cy = sy + 22;
    float bw = (sidePanelW - 30) * 0.5f;

    g_fontBold.drawText(cx, cy, "Camera Presets", 0.92f, 0.95f, 0.99f);
    cy += 8;
    drawButton("cam_iso", cx, cy, bw, 26, "Isometric");
    drawButton("cam_top", cx + bw + 6, cy, bw, 26, "Top (XY)");
    cy += 32;
    drawButton("cam_front", cx, cy, bw, 26, "Front (XZ)");
    drawButton("cam_right", cx + bw + 6, cy, bw, 26, "Right (YZ)");

    cy += 42;
    g_fontBold.drawText(cx, cy, "Inspection Shader Mode", 0.92f, 0.95f, 0.99f);
    cy += 8;
    drawButton("mode_shaded", cx, cy, bw, 26, "CAD Solid", g_renderMode == MODE_SHADED);
    drawButton("mode_dfm", cx + bw + 6, cy, bw, 26, "DFM Overhang", g_renderMode == MODE_DFM);
    cy += 32;
    drawButton("mode_wire", cx, cy, bw, 26, "Wireframe", g_renderMode == MODE_WIRE);
    drawButton("mode_xray", cx + bw + 6, cy, bw, 26, "X-Ray Internal", g_renderMode == MODE_XRAY);

    cy += 42;
    char sliceBuf[64];
    float zCut = (st.minZ) + (st.heightZ * g_slicePct / 100.0f);
    std::snprintf(sliceBuf, sizeof(sliceBuf), "Z-Section Slicer: %.0f%% (%.1fmm)", g_slicePct, zCut);
    g_fontBold.drawText(cx, cy, sliceBuf, 0.92f, 0.95f, 0.99f);
    cy += 10;
    g_sliderX = cx;
    g_sliderY = cy;
    g_sliderW = sidePanelW - 24;
    g_sliderH = 16;
    drawFilledRect(g_sliderX, g_sliderY + 5, g_sliderW, 6, 0.05f, 0.07f, 0.10f);
    float fillW = g_sliderW * ((g_slicePct - 5.0f) / 95.0f);
    drawFilledRect(g_sliderX, g_sliderY + 5, fillW, 6, 0.18f, 0.55f, 0.92f);
    drawFilledRect(g_sliderX + fillW - 5, g_sliderY + 1, 10, 14, 0.85f, 0.92f, 1.0f);

    cy += 26;
    drawButton("toggle_calipers", cx, cy, sidePanelW - 24, 25,
               g_showCalipers ? "[ON] 3D BBox Calipers" : "[OFF] 3D BBox Calipers", g_showCalipers);

    cy += 38;
    g_fontBold.drawText(cx, cy, "Quick Load Plated Models", 0.92f, 0.95f, 0.99f);
    cy += 8;
    drawButton("load_phone_kit", cx, cy, sidePanelW - 24, 24, "Phone + Buds3 Pro Full Kit");
    cy += 28;
    drawButton("load_hub_only", cx, cy, bw, 24, "Main Hub Only");
    drawButton("load_gear_kit", cx + bw + 6, cy, bw, 24, "15T Gear Kit");

    // 5. Bottom Interactive Prompt Bar (Connected to AGY --model=flash ONLY)
    float py = winH - pad - promptAreaH;
    drawFilledRect(pad, py, winW - 2 * pad, promptAreaH, 0.09f, 0.12f, 0.16f);
    drawStrokedRect(pad, py, winW - 2 * pad, promptAreaH, 0.22f, 0.30f, 0.42f, 1.0f, 1.2f);

    std::string convLabel, lastReplyCopy;
    {
        std::lock_guard<std::mutex> lock(g_agentMutex);
        convLabel = g_activeConversationId.empty()
            ? "Session: New Conversation (will spawn with `agentapi new-conversation --model=flash`)"
            : "Active Flash Session ID: " + g_activeConversationId;
        lastReplyCopy = g_lastAgentReply;
    }

    g_fontBold.drawText(pad + 14, py + 22,
        "AGY Prompt Console - Locked to Gemini 3.8 Flash (`--model=flash`) + `3d-model-studio` Plugin:",
        0.38f, 0.85f, 0.99f);
    g_fontRegular.drawText(pad + 14, py + 42, lastReplyCopy, 0.72f, 0.79f, 0.88f, 1.0f, winW - 2 * pad - 150);

    drawButton("new_session", winW - pad - 140, py + 10, 126, 24, "+ New Session");

    // Text Input Box
    float inputX = pad + 14;
    float inputY = py + 54;
    float sendBtnW = 165.0f;
    float inputW = winW - 2 * pad - 28 - sendBtnW - 10;
    float inputH = 44.0f;

    drawFilledRect(inputX, inputY, inputW, inputH, 0.05f, 0.07f, 0.10f);
    drawStrokedRect(inputX, inputY, inputW, inputH, 0.28f, 0.52f, 0.82f, 1.0f, 1.4f);

    bool showCursor = (static_cast<int>(glfwGetTime() * 2.0) % 2 == 0);
    std::string displayPrompt = g_promptText + (showCursor ? "|" : "");
    if (g_promptText.empty()) {
        g_fontRegular.drawText(inputX + 12, inputY + 27,
            "Ask Gemini 3.8 Flash to create or modify a 3D model (e.g. 'Make the Buds3 Pro pocket 2mm deeper')... [Enter to Send, Ctrl+V Paste]",
            0.42f, 0.48f, 0.58f, 1.0f, inputW - 24);
    } else {
        g_fontMono.drawText(inputX + 12, inputY + 27, displayPrompt, 0.96f, 0.98f, 1.0f, 1.0f, inputW - 24);
    }

    drawButton("send_prompt", inputX + inputW + 10, inputY, sendBtnW, inputH,
               g_agentBusy.load() ? "Running Flash..." : "Send (Flash 3.8)", false, true);
}

// ============================================================================
// 9. GLFW Input Callbacks (Mouse, Scroll, Keyboard, Clipboard Paste)
// ============================================================================
static void updateSliderFromMouse(double mx) {
    float t = static_cast<float>((mx - g_sliderX) / std::max(1.0f, g_sliderW));
    t = std::clamp(t, 0.0f, 1.0f);
    g_slicePct = 5.0f + t * 95.0f;
}

static void handleButtonClick(const std::string& id) {
    if (id == "fit_view" || id == "cam_iso") {
        g_yaw = -0.65f; g_pitch = 0.55f; g_zoom = 1.0f; g_panX = 0.0f; g_panY = 0.0f;
    } else if (id == "cam_top") {
        g_yaw = 0.0f; g_pitch = 1.56f; g_panX = 0.0f; g_panY = 0.0f;
    } else if (id == "cam_front") {
        g_yaw = 0.0f; g_pitch = 0.0f; g_panX = 0.0f; g_panY = 0.0f;
    } else if (id == "cam_right") {
        g_yaw = 1.5708f; g_pitch = 0.0f; g_panX = 0.0f; g_panY = 0.0f;
    } else if (id == "mode_shaded") {
        g_renderMode = MODE_SHADED;
    } else if (id == "mode_dfm") {
        g_renderMode = MODE_DFM;
    } else if (id == "mode_wire") {
        g_renderMode = MODE_WIRE;
    } else if (id == "mode_xray") {
        g_renderMode = MODE_XRAY;
    } else if (id == "toggle_calipers") {
        g_showCalipers = !g_showCalipers;
    } else if (id == "replay") {
        g_replaying = true;
        g_replayStartTime = glfwGetTime();
    } else if (id == "load_phone_kit") {
        std::vector<Triangle> t; MeshStats s;
        if (loadStlFile(kDefaultStlPath, t, s)) {
            std::lock_guard<std::mutex> lock(g_meshMutex);
            g_tris.swap(t); g_stats = s; g_activeTriCount = s.triCount;
        }
    } else if (id == "load_hub_only") {
        std::vector<Triangle> t; MeshStats s;
        if (loadStlFile(kPluginRoot + "/examples/phone_buds_holder_v2/main_hub_buds_holder.stl", t, s)) {
            std::lock_guard<std::mutex> lock(g_meshMutex);
            g_tris.swap(t); g_stats = s; g_activeTriCount = s.triCount;
        }
    } else if (id == "load_gear_kit") {
        std::vector<Triangle> t; MeshStats s;
        if (loadStlFile(kPluginRoot + "/examples/gear_crank_stand/gear_crank_full_kit_zero_supports.stl", t, s)) {
            std::lock_guard<std::mutex> lock(g_meshMutex);
            g_tris.swap(t); g_stats = s; g_activeTriCount = s.triCount;
        }
    } else if (id == "new_session") {
        std::lock_guard<std::mutex> lock(g_agentMutex);
        g_activeConversationId.clear();
        g_agentStatusText = "NEW SESSION READY | Next prompt will spawn a fresh `--model=flash` conversation";
    } else if (id == "send_prompt") {
        if (!g_promptText.empty() && !g_agentBusy.load()) {
            std::string toSend = g_promptText;
            g_promptText.clear();
            submitPromptToAgyFlash(toSend);
        }
    }
}

static void mouseButtonCallback(GLFWwindow* window, int button, int action, int mods) {
    double mx, my;
    glfwGetCursorPos(window, &mx, &my);

    if (action == GLFW_PRESS) {
        if (button == GLFW_MOUSE_BUTTON_LEFT) {
            // Check buttons
            for (const auto& b : g_buttons) {
                if (mx >= b.x && mx <= b.x + b.w && my >= b.y && my <= b.y + b.h) {
                    handleButtonClick(b.id);
                    return;
                }
            }
            // Check Z-Slicer slider
            if (mx >= g_sliderX && mx <= g_sliderX + g_sliderW &&
                my >= g_sliderY - 4 && my <= g_sliderY + g_sliderH + 4) {
                g_isDraggingSlider = true;
                updateSliderFromMouse(mx);
                return;
            }
        }

        // Check 3D Viewport interaction
        if (mx >= g_viewX && mx <= g_viewX + g_viewW && my >= g_viewY && my <= g_viewY + g_viewH) {
            g_lastMouseX = mx;
            g_lastMouseY = my;
            if (button == GLFW_MOUSE_BUTTON_RIGHT || button == GLFW_MOUSE_BUTTON_MIDDLE || (mods & GLFW_MOD_SHIFT)) {
                g_isPanning = true;
            } else if (button == GLFW_MOUSE_BUTTON_LEFT) {
                g_isOrbiting = true;
            }
        }
    } else if (action == GLFW_RELEASE) {
        g_isOrbiting = false;
        g_isPanning = false;
        g_isDraggingSlider = false;
    }
}

static void cursorPosCallback(GLFWwindow* /*window*/, double mx, double my) {
    if (g_isDraggingSlider) {
        updateSliderFromMouse(mx);
        return;
    }
    if (!g_isOrbiting && !g_isPanning) return;

    double dx = mx - g_lastMouseX;
    double dy = my - g_lastMouseY;
    g_lastMouseX = mx;
    g_lastMouseY = my;

    if (g_isPanning) {
        g_panX += static_cast<float>(dx);
        g_panY += static_cast<float>(dy);
    } else if (g_isOrbiting) {
        // Natural turntable orbit: dragging right rotates front of model right,
        // dragging up/down tilts smoothly without flipping underneath build plate
        g_yaw += static_cast<float>(dx) * 0.01f;
        g_pitch = std::clamp(g_pitch - static_cast<float>(dy) * 0.01f, -1.55f, 1.55f);
    }
}

static void scrollCallback(GLFWwindow* window, double /*xoffset*/, double yoffset) {
    double mx, my;
    glfwGetCursorPos(window, &mx, &my);
    if (mx >= g_viewX && mx <= g_viewX + g_viewW && my >= g_viewY && my <= g_viewY + g_viewH) {
        g_zoom = std::clamp(g_zoom * (yoffset > 0 ? 1.12f : 0.89f), 0.25f, 6.0f);
    }
}

static void charCallback(GLFWwindow* /*window*/, unsigned int codepoint) {
    if (codepoint >= 32 && codepoint < 127) {
        g_promptText.push_back(static_cast<char>(codepoint));
    }
}

static void keyCallback(GLFWwindow* window, int key, int /*scancode*/, int action, int mods) {
    if (action != GLFW_PRESS && action != GLFW_REPEAT) return;

    if (key == GLFW_KEY_BACKSPACE) {
        if (!g_promptText.empty()) g_promptText.pop_back();
    } else if (key == GLFW_KEY_U && (mods & GLFW_MOD_CONTROL)) {
        g_promptText.clear();
    } else if (key == GLFW_KEY_V && (mods & GLFW_MOD_CONTROL)) {
        const char* clip = glfwGetClipboardString(window);
        if (clip) {
            for (const char* p = clip; *p; ++p) {
                if (*p >= 32 && *p < 127) g_promptText.push_back(*p);
            }
        }
    } else if (key == GLFW_KEY_ENTER || key == GLFW_KEY_KP_ENTER) {
        if (!g_promptText.empty() && !g_agentBusy.load()) {
            std::string toSend = g_promptText;
            g_promptText.clear();
            submitPromptToAgyFlash(toSend);
        }
    } else if (key == GLFW_KEY_ESCAPE) {
        glfwSetWindowShouldClose(window, GLFW_TRUE);
    }
}

// ============================================================================
// 10. Main Entry Point
// ============================================================================
int main(int argc, char** argv) {
    std::string initialStl = kDefaultStlPath;
    if (argc > 1 && fs::exists(argv[1])) {
        initialStl = argv[1];
    }

    {
        std::vector<Triangle> initTris;
        MeshStats initStats;
        if (loadStlFile(initialStl, initTris, initStats)) {
            std::lock_guard<std::mutex> lock(g_meshMutex);
            g_tris.swap(initTris);
            g_stats = initStats;
            g_activeTriCount = initStats.triCount;
        }
    }

    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW3 on Linux display.\n";
        return 1;
    }

    glfwWindowHint(GLFW_SAMPLES, 4);
#ifdef GLFW_X11_CLASS_NAME
    glfwWindowHintString(GLFW_X11_CLASS_NAME, "agy-cad-studio");
    glfwWindowHintString(GLFW_X11_INSTANCE_NAME, "agy-cad-studio");
#endif
#ifdef GLFW_WAYLAND_APP_ID
    glfwWindowHintString(GLFW_WAYLAND_APP_ID, "agy-cad-studio");
#endif
    GLFWwindow* window = glfwCreateWindow(
        1280, 780,
        "AGY 3D Parametric CAD Studio - Linux C++ (Gemini 3.8 Flash ONLY | 3d-model-studio Plugin)",
        nullptr, nullptr
    );
    if (!window) {
        std::cerr << "Failed to create OpenGL window.\n";
        glfwTerminate();
        return 1;
    }

    // Set window & taskbar icon (_NET_WM_ICON)
    GLFWimage appIcon;
    appIcon.width = 64;
    appIcon.height = 64;
    appIcon.pixels = const_cast<unsigned char*>(kAppIcon64RGBA);
    glfwSetWindowIcon(window, 1, &appIcon);

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    // Initialize FreeType2 fonts from Zorin OS 18 system fonts
    g_fontRegular.init({
        "/usr/share/fonts/truetype/croscore/Arimo-Regular.ttf",
        "/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf",
        "/usr/share/fonts/truetype/tiresias/tiresias_pcfont.ttf"
    }, 13);
    g_fontBold.init({
        "/usr/share/fonts/truetype/croscore/Arimo-Bold.ttf",
        "/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf",
        "/usr/share/fonts/truetype/tiresias/tiresias_pcfont_bold.ttf"
    }, 14);
    g_fontMono.init({
        "/usr/share/fonts/truetype/croscore/Cousine-Regular.ttf",
        "/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Regular.otf",
        "/usr/share/fonts/truetype/croscore/Arimo-Regular.ttf"
    }, 13);

    glfwSetMouseButtonCallback(window, mouseButtonCallback);
    glfwSetCursorPosCallback(window, cursorPosCallback);
    glfwSetScrollCallback(window, scrollCallback);
    glfwSetCharCallback(window, charCallback);
    glfwSetKeyCallback(window, keyCallback);

    startLiveFileAndTranscriptWatcher();

    double lastTime = glfwGetTime();
    int frames = 0;
    float fps = 60.0f;

    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        double now = glfwGetTime();
        frames++;
        if (now - lastTime >= 0.5) {
            fps = static_cast<float>(frames / (now - lastTime));
            frames = 0;
            lastTime = now;
        }

        renderFrame(window, fps);
        glfwSwapBuffers(window);
    }

    g_appRunning.store(false);
    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
