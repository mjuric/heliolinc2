#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <string>
#include <span>
#include <optional>

#include "solarsyst_dyn_geo01.h"
namespace py = pybind11;

int add(int i, int j)
{
	return i + j;
}

int maketrack03a(const std::vector<const std::string> &argv, std::optional<py::array_t<det_OC_index, py::array::c_style>> py_detvec);

void numpy2detvec(py::array_t<det_OC_index, py::array::c_style> &arr)
{
  auto r = arr.mutable_unchecked<1>();
  std::cout << "HERE!\n";
  std::cout << arr.strides(0) << "\n";
  std::cout << arr.dtype() << "\n";
  std::cout << arr.size() << "\n";

  std::span<det_OC_index> s{&r[0], static_cast<unsigned long>(r.size())};

  for(int i = 0; i < s.size(); i++)
  {
    auto &v = s[i];
    std::cout << v.MJD << " " << v.idstring << " " << v.RA << " " << v.Dec << " " << v.index << "\n";
    if(i == 10) break;
  }
  return;

  for(int i = 0; i < r.shape(0); i++)
  {
    auto &v = r[i];
    std::cout << v.MJD << " " << v.idstring << " " << v.RA << " " << v.Dec << "\n";
    if(i == 10) break;
  }
}

PYBIND11_MODULE(hela, m)
{
	m.doc() = "HelioLINC Advanced (hela)"; // optional module docstring

	PYBIND11_NUMPY_DTYPE(det_OC_index, MJD, RA, Dec, x, y, z, idstring, index);

	m.def("add", &add, "A function that adds two numbers");
	m.def("maketrack03a", &maketrack03a, "The maketracks function", py::arg("argv"), py::arg("detvec").none(true) = py::none());
	m.def("dp", &numpy2detvec, "Test fun");
}
