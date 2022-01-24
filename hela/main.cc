#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <string>
#include <optional>

#include "solarsyst_dyn_geo01.h"
namespace py = pybind11;

int add(int i, int j)
{
	return i + j;
}

int maketrack03a(
  const py::array &py_detvec,
  const std::string &earthfile,
  const std::string &inimfile="",
  const std::string &outimfile="",
  const std::string &outpairfile="",
  const std::string &pairdetfile="",
  const REAL imrad=2.0,
  REAL maxtime=1.5,
  const REAL maxvel=1.5,
  const std::array<REAL, 3> observatory = {289.26345, 0.86502, -0.500901}
);

void numpy2detvec(py::array &arr)
{
//  auto r = arr.mutable_unchecked<1>();
  std::cout << "HERE!\n";
  std::cout << arr.strides(0) << "\n";
  std::cout << arr.dtype() << "\n";
  std::cout << arr.size() << "\n";
  std::cout << arr.ndim() << "\n";
  std::cout << "shape: " << arr.shape(0) << "\n";
  std::cout << "itemsize: " << arr.itemsize() << "\n";

  using namespace pybind11::literals;
  auto mjd = arr["MJD"].attr("astype")("f8", "copy"_a=false).cast<py::array_t<double>>();
  auto ra = arr["RA"].attr("astype")("f8", "copy"_a=false).cast<py::array_t<double>>();
  auto dec = arr["Dec"].attr("astype")("f8", "copy"_a=false).cast<py::array_t<double>>();

  std::cout << "mjd dtype: " << mjd.dtype() << "\n";
//  std::cout << "mjd data:  " << mjd[0] << " " << mjd[1] << " "  << mjd[2] << " ... " << "\n";
  auto r = mjd.mutable_unchecked<1>();
  std::cout << "mjd data:  " << r[0] << "\n";

  auto dt = arr.data(1);
  std::cout << dt << "\n";
  std::cout << arr.data(1) << " " << arr.data(0) << "\n";

}

PYBIND11_MODULE(hela, m)
{
	m.doc() = "HelioLINC Advanced (hela)"; // optional module docstring

	PYBIND11_NUMPY_DTYPE(det_OC_index, MJD, RA, Dec, x, y, z, idstring, index);

	m.def("add", &add, "A function that adds two numbers");
	m.def("maketrack03a", &maketrack03a, "The maketracks function");
	m.def("dp", &numpy2detvec, "Test fun");
}
