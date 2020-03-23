#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 15:31:55 2020

@author: borderiesm

calcul de scores
"""


import numpy

global threshold

def contable(o,m,thresh):
  # computes contingency table from o observation list, m model list and threshold
  a=float(len([v for i,v in enumerate(o) if o[i]< thresh and m[i]< thresh]))
  b=float(len([v for i,v in enumerate(o) if o[i]< thresh and m[i]>=thresh]))
  c=float(len([v for i,v in enumerate(o) if o[i]>=thresh and m[i]< thresh]))
  d=float(len([v for i,v in enumerate(o) if o[i]>=thresh and m[i]>=thresh]))
  return a,b,c,d

def far(o,m):
  # taux de fausses alarmes
  a,b,c,d=contable(o,m,threshold)
  #print threshold, len(o), len(m),type(o),type(m), a, b , c, d
  if b+d>0:
    #print 'pas d erreur'
    return b/(b+d)
  else:
    #print 'Error in faromt ',threshold, len(o), len(m), b, d
    #sys.exit()
    return numpy.nan#float('NaN')

def pod(o, m):
  # taux de de détections
  a,b,c,d=contable(o,m,threshold)
  if c+d>0:
    return d/(c+d)
  else:
    return numpy.nan#float('NaN')


def hss(o,m):
  a,b,c,d=contable(o,m,threshold)
  if (b+c)*(a+b+c+d)+2*(a*d-b*c)>0:
    return 2*(a*d-b*c)/((b+c)*(a+b+c+d)+2*(a*d-b*c))
  else:
    return numpy.nan#float('NaN')
				
#CommonKeys = CommonKeys &  cumul_obs[itime].viewkeys()
