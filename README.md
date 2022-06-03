Creation and testing of modular pieces for C++ implementation of heliolinc3D.

maketrack02b.cpp: Perform image-based pairing to create tracklets.

readpairs01a.cpp: Read pairing output files to realize tracklets.

maketrack03a.cpp: Updated tracklet creation, stores observer barycentric
                  positions and string IDs enabling the mapping of created
		  tracklets to specific simulated objects.

projectpairs04b.cpp: First complete implementation of heliolinc in C++.
		     Requires input files produced by maketrack03a.

projectpairs04c.cpp: Experimental improvement on projectpairs04b, using
		     integerized versions of state vectors to speed searching.

Suggested compile commands:
c++ -O3 -o maketrack03a maketrack03a.cpp solarsyst_dyn_geo01.cpp -std=c++11
c++ -O3 -o projectpairs04b projectpairs04b.cpp solarsyst_dyn_geo01.cpp -std=c++11
c++ -O3 -o projectpairs04c projectpairs04c.cpp solarsyst_dyn_geo01.cpp -std=c++11

### WIP: Building and testing on epyc

```
#
# get the code
#
git get mjuric/heliolinc2
cd /astro/users/mjuric/projects/github.com/mjuric/heliolinc2
git checkout u/mjuric/packaging

#
# make the conda environment
#
mamba create -n hela -c conda-forge cxx-compiler sysroot_linux-64=2.17 pandas pybind11
conda activate hela

#
# link the directory with test files
#
ln -s /epyc/users/mjuric/heliolinc2/tests/

#
# build the c++ sources (these are Ari's unmodified codes, just moved to
# src/ and with a proper Makefile added)
#
cd src
make
export LD_LIBRARY_PATH="$PWD:$LD_LIBRARY_PATH"
./maketrack03a -dets ../tests/sample.csv -earth ../tests/Earth2hr2020s_01a.txt

#
# Build python bindings
#
cd ../hela
make
./maketrack.py --dets ../tests/sample.csv --earth ../tests/Earth2hr2020s_01a.txt

#
# Make sure the outputs are identical (no output == GOOD!)
#
cmp indextest01.txt ../src/indextest01.txt; cmp outpairfile01.txt ../src/outpairfile01.txt; cmp pairdetfile01.txt ../src/pairdetfile01.txt; cmp testjunk01.txt ../src/testjunk01.txt
```
