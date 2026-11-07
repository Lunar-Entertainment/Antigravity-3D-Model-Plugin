CXX = g++
CXXFLAGS = -O3 -std=c++20 -Wall -Wextra $(shell pkg-config --cflags glfw3 gl glu freetype2)
LDFLAGS = $(shell pkg-config --libs glfw3 gl glu freetype2) -lpthread

TARGET = agy_cad_studio
SRC = agy_cad_studio.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET) $(LDFLAGS)

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)
