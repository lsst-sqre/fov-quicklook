#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include "fitsfile.h"

static PyObject *decompressed_fits(PyObject *self, PyObject *args)
{
  const char *filepath;
  int num_threads;

  // Python引数の解析
  if (!PyArg_ParseTuple(args, "si", &filepath, &num_threads))
  {
    return NULL;
  }

  struct FitsFileOpenOptions options = {.num_threads = num_threads};
  struct stat fileStat;
  struct IRegFile *file = NULL;
  const char *error_message = NULL;
  PyObject *result = NULL;

  file = fitsfile_open(filepath, NULL, &options);
  if (file == NULL)
  {
    error_message = "Failed to open the file.";
    goto end;
  }

  if (file->vtbl->fstat(file, &fileStat) != 0)
  {
    error_message = "Failed to get the file stat.";
    goto end;
  }

  result = PyBytes_FromStringAndSize(NULL, fileStat.st_size);
  if (result == NULL)
  {
    error_message = "Failed to allocate memory for the result.";
    goto end;
  }

  char *buf = PyBytes_AS_STRING(result);
  const size_t read_bytes = file->vtbl->read(file, buf, fileStat.st_size, 0);
  if (read_bytes < fileStat.st_size)
  {
    error_message = "Failed to read the entire file.";
    goto end;
  }

end:
  if (file)
  {
    file->vtbl->close(file);
  }
  if (error_message != NULL)
  {
    if (result)
    {
      Py_DECREF(result);
    }
    PyErr_SetString(PyExc_RuntimeError, error_message);
    return NULL;
  }
  return result;
}

// モジュール内で定義される関数リスト
static PyMethodDef FitsMethods[] = {
    {"decompressed_fits", decompressed_fits, METH_VARARGS, "Decompress a fits file."},
    {NULL, NULL, 0, NULL} // 終端
};

// モジュール定義
static struct PyModuleDef FitsModule = {
    PyModuleDef_HEAD_INIT,
    "mineo_fits_decompress_c", // モジュール名
    NULL,                      // モジュールのドキュメント (NULL でも可)
    -1,                        // グローバルな状態を持たないモジュールなら -1
    FitsMethods                // メソッド
};

// モジュール初期化関数
PyMODINIT_FUNC PyInit_mineo_fits_decompress_c(void)
{
  return PyModule_Create(&FitsModule);
}