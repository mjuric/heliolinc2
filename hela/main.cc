#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <string>

#include "solarsyst_dyn_geo01.h"

int add(int i, int j)
{
	return i + j;
}

int maketrack03a(const std::vector<const std::string> &argv);

PYBIND11_MODULE(hela, m)
{
	m.doc() = "HelioLINC Advanced (hela)"; // optional module docstring

	m.def("add", &add, "A function that adds two numbers");
	m.def("maketrack03a", &maketrack03a, "The maketracks function");

	PYBIND11_NUMPY_DTYPE(det_OC_index, MJD, RA, Dec, x, y, z, idstring, index);
}
