#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <string>

#include "solarsyst_dyn_geo01.h"
namespace py = pybind11;

int add(int i, int j)
{
	return i + j;
}

int maketrack03a(const std::vector<const std::string> &argv);

void numpy2detvec(const py::array_t<det_OC_index, 0> &arr)
{
  auto r = arr.unchecked<1>();
  std::cout << "HERE!\n";
  std::cout << arr.strides(0) << "\n";
  std::cout << arr.dtype() << "\n";
  for(int i = 0; i < r.shape(0); i++)
  {
    auto &v = r(i);
    std::cout << v.MJD << " " << v.idstring << " " << v.RA << " " << v.Dec << "\n";
    if(i == 10) break;
  }
}

PYBIND11_MODULE(hela, m)
{
	m.doc() = "HelioLINC Advanced (hela)"; // optional module docstring

	PYBIND11_NUMPY_DTYPE(det_OC_index, MJD, RA, Dec, x, y, z, idstring, index);

	m.def("add", &add, "A function that adds two numbers");
	m.def("maketrack03a", &maketrack03a, "The maketracks function");
	m.def("dp", &numpy2detvec, "Test fun");
}
