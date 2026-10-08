"""Miscelaneous functions.
string/list
parallelization
"""
import os,logging

logger=logging.getLogger(__name__)

def iter_flatten(iterable):
  it = iter(iterable)
  for e in it:
    if isinstance(e, (list, tuple)):
      for f in iter_flatten(e):
        yield f
    else:
      yield e
      
def desc_to_path(desc):
  """TODO: path separator platform independent"""
  return os.path.join(*['_'.join(iter_flatten(subdesc)).replace(' ','=').replace('/','-') for subdesc in desc])

def desc_to_string(desc):
  return ', '.join(iter_flatten(desc))
  
def desc_to_x(desc,style='list'):
  """Convert structured description list to given style.
  
  Args:
    style (string): one of 'list', 'string', or 'path'
  
  Returns:
    Depends on style:
        list: nested list of strings
        string: concatenation of list into single string
        path: conversion of list into sensible path
  """
  if style=='list':
    return desc
  elif style=='string':
    return desc_to_string(desc)
  elif style=='path':
    return desc_to_path(desc)
  else:
    raise ValueError('Unknown style %s'%style)
    
def join_with_underscores(*args):
  if len(args)==0:
    return ''
  r=args[0]
  for arg in args[1:]:
    if len(arg)==0:
      continue
    if not r[-1].isdigit()^arg[0].isdigit():
      r+='_'
    r+=arg
  return r
    
  

  
  

  
  

  
