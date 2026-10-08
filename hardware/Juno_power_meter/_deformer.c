#include <Python.h>
#include "deformer.h"
#include <visa.h>
#include <TLDFM.h>
#include <TLDFMX.h>
#include <TLDSTP.h>

static char module_docstring[] =
    "This module provides an interface for running a genetic algorithm on a thorlabs deformable mirror.";
static char deformer_docstring[] =
    "Run the genetic algorithm.";

static PyObject *deformer_deformer(PyObject *self, PyObject *args);

static PyMethodDef module_methods[] = {
    {"deformer",deformer_deformer, METH_VARARGS, deformer_docstring},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC PyInit__deformer(void)
{
    
    PyObject *module;
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_deformer",
        module_docstring,
        -1,
        module_methods,
        NULL,
        NULL,
        NULL,
        NULL
    };
    module = PyModule_Create(&moduledef);
    if (!module) return NULL;

    /* Load `numpy` functionality. */

    return module;
}

static PyObject *deformer_deformer(PyObject *self, PyObject *args)
{

    deformer();
    return 0;

}