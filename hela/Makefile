PYINCLUDES = $(shell python3 -m pybind11 --includes) 
PYEXTSUFFIX = $(shell python3-config --extension-suffix)
PLATFORMLDFLAGS = -undefined dynamic_lookup 

# $(CXX) -shared $(CXXFLAGS) $(CPPFLAGS) -std=gnu++17 $(PLATFORMFLAGS) $(PYINCLUDES) example.cc -o example$(PYEXTSUFFIX)

PREFIX  = ..
SOURCES = main.cc solarsyst_dyn_geo01.cc maketrack03a.cc
MODULE = hela$(PYEXTSUFFIX)

.PHONY: all
all: $(MODULE)

$(MODULE): $(SOURCES:%.cc=%.o)
	$(CXX) -shared $(PLATFORMLDFLAGS) -fPIC $(LDFLAGS) -install_name "@rpath/$(MODULE)" $(OUTPUT_OPTION) $^

clean:
	rm -f $(SOURCES:%.cc=%.o)
	rm -rf .deps 

DEPDIR := .deps
DEPFLAGS = -MT $@ -MMD -MP -MF $(DEPDIR)/$*.Td
POSTCOMPILE = mv -f $(DEPDIR)/$*.Td $(DEPDIR)/$*.d && touch $@

%.o : %.cc
%.o : %.cc $(DEPDIR)/%.d | $(DEPDIR)
	$(CXX) $(DEPFLAGS) $(CXXFLAGS) $(CPPFLAGS) $(TARGET_ARCH) $(PYINCLUDES) -I../include -std=gnu++2a -c $(OUTPUT_OPTION) $<
	$(POSTCOMPILE)

$(DEPDIR): ; @mkdir -p $@

DEPFILES := $(SOURCES:%.cc=$(DEPDIR)/%.d)
$(DEPFILES):

include $(wildcard $(DEPFILES))
