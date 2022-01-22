#
# A simple makefile for "HelioLinc Advanced"
#
# Builds the heliolinc library (libhela.dylib) and the binaries.
#

# List all the command-line programs here
PROGRAMS = maketrack03a projectpairs04b projectpairs04c

# List all the common library sources here
LIB = libhela.dylib
LIB_SOURCES = solarsyst_dyn_geo01.cpp

##
## The code below doesn't need to be touched unless you're changing the way
## the build works.
##
## Learn more about automatic dependency generation details?  See:
## http://make.mad-scientist.net/papers/advanced-auto-dependency-generation/#combine
##
## Building library code:
## https://www.oreilly.com/library/view/c-cookbook/0596007612/ch01s18.html
##

PREFIX  = ..
SOURCES = $(LIB_SOURCES) $(PROGRAMS:%=%.cpp)

.PHONY: all
all: $(PROGRAMS)

.PHONY: install
install: $(LIB) $(PROGRAMS)
	mkdir -p $(PREFIX)/{lib,bin}
	cp -p $(LIB) $(PREFIX)/lib
	cp -p $(PROGRAMS) $(PREFIX)/bin

$(PROGRAMS): %: %.o libhela.dylib
	$(CXX) -L. -lhela -Wl,-rpath,.,-rpath,"@loader_path/../lib" -o $@ $<

$(LIB): $(LIB_SOURCES:%.cpp=%.o)
	$(CXX) -dynamiclib -fPIC $(LDFLAGS) -install_name "@rpath/$(LIB)" $(OUTPUT_OPTION) $^

clean:
	rm -f $(PROGRAMS) $(SOURCES:%.cpp=%.o)
	rm -rf .deps 

DEPDIR := .deps
DEPFLAGS = -MT $@ -MMD -MP -MF $(DEPDIR)/$*.Td
POSTCOMPILE = mv -f $(DEPDIR)/$*.Td $(DEPDIR)/$*.d && touch $@

%.o : %.cpp
%.o : %.cpp $(DEPDIR)/%.d | $(DEPDIR)
	$(CXX) $(DEPFLAGS) $(CXXFLAGS) $(CPPFLAGS) $(TARGET_ARCH) -std=gnu++17 -I../include -c $(OUTPUT_OPTION) $<
	$(POSTCOMPILE)

$(DEPDIR): ; @mkdir -p $@

DEPFILES := $(SOURCES:%.cpp=$(DEPDIR)/%.d)
$(DEPFILES):

include $(wildcard $(DEPFILES))
