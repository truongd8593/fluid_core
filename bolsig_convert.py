#!/usr/bin/env python

# Made by Jannis.
# Description: Convert Bolsig+ output (the big table) to a form we can use in our fluid codes
# TODO:
# Could write this more compactly, but for now works okay.

import argparse
import re
import numpy as np
from StringIO import StringIO

def getArgs():
   "Set the arguments, read them in, and return them"
   parser = argparse.ArgumentParser(description = "Converter for Bolsig+ data")
   parser.add_argument("infile", type = str, help = "input file")
   parser.add_argument("outfile", type = str, help = "output file")
   parser.add_argument("-g", dest = "gas_name", type = str, default = "GAS", help = "for output: gas name")
   parser.add_argument("-p", dest = "gas_pressure", type = float, default = 1.0, help = "for output: gas pressure (bar)")

   return parser.parse_args()

def convert():
   cfg = getArgs()

   with open(cfg.infile, 'r') as f:
      fr = f.read()
      fr = re.sub(r'(\r\n|\r|\n)', '\n', fr) # Fix newlines

      # Look up gas temperature and determine file type
      match = re.search(r'Gas temperature \(K\)\s*(.*)', fr)
      if (match):
         syntax = 'bolsig+'
      else:
         syntax = 'www'
         match = re.search(r'Tgas\s+(\S+)\s+K', fr)

      gas_temp = float(match.group(1))

      # Look up columns of things we are interested in
      if syntax == 'bolsig+':
         Efield_label = 'E/N(Td)'
         match = re.search(r'(A\S*).*Mean energy \(eV\)', fr)
         eV_label = match.group(1)
         match = re.search(r'(A\S*).*Mobility x N \(1\/m\/V\/s\)', fr)
         mu_label = match.group(1)
         match = re.search(r'(A\S*).*Diffusion coefficient x N \(1\/m\/s\)', fr)
         dc_label = match.group(1)
         match = re.search(r'(A\S*).*Spatial growth coef. \(m2\)', fr)
         alpha_label = match.group(1)
         eta_label = 'I_DO_NOT_EXIST?'

         # Find start of table
         match = re.search(r'.*(\s+(A\d+)){5,}.*', fr) # Listing of columns at the start
         header = re.sub(r'E/N \(', r'E/N(', match.group(0))
         tbl_start = match.end() + 1
      else:
         Efield_label = 'E/N'
         eV_label = 'Ee'
         mu_label = 'muN'
         dc_label = 'DN'
         alpha_label = 'alpha/N'
         eta_label = 'eta/N'

         # Find start of table
         match = re.search(r'#\s+E\/N\s+Ee.*', fr) # Listing of columns at the start
         header = match.group(0)
         match = re.search(r'#\s+Td\s+eV.*', fr) # Listing of units at the start
         tbl_start = match.end() + 1

      # Find indexes of columns
      column_order = header.split()
      Efield_col = column_order.index(Efield_label)
      eV_col = column_order.index(eV_label)
      mu_col = column_order.index(mu_label)
      dc_col = column_order.index(dc_label)
      alpha_col = column_order.index(alpha_label)
      if eta_label in column_order:
         eta_col = column_order.index(eta_label)
      else:
         eta_col = -1

      # Find end of table
      match = re.search(r'^\s*$', fr[tbl_start:], re.M) # Double Newline at the end
      tbl_end = tbl_start + match.start() - 1
      tbl_data = np.genfromtxt(StringIO(fr[tbl_start:tbl_end]))

   boltzmann_const = 1.3806488e-23
   gas_num_dens = cfg.gas_pressure * 1e5 / (boltzmann_const * gas_temp) # Ideal gas law

   print("Gas temperature %.3e Kelvin" % (gas_temp))
   print("Gas pressure    %.3e bar" % (cfg.gas_pressure))
   print("Gas #density    %.3e /m3" % (gas_num_dens))

   with open(cfg.outfile, 'w') as f:
      f.close() # Clear file

   with open(cfg.outfile, 'a') as f:
      tbl_data[:, Efield_col] = tbl_data[:, Efield_col] * 1e-21 * gas_num_dens
      tbl_data[:, mu_col] = tbl_data[:, mu_col] / gas_num_dens
      tbl_data[:, dc_col] = tbl_data[:, dc_col] / gas_num_dens
      tbl_data[:, alpha_col] = tbl_data[:, alpha_col] * gas_num_dens

      write_entry(r'Efield[V/m]_vs_mu[m2/Vs]', tbl_data[:, Efield_col], tbl_data[:, mu_col], cfg.gas_name, f)
      write_entry(r'Efield[V/m]_vs_dif[m2/s]', tbl_data[:, Efield_col], tbl_data[:, dc_col], cfg.gas_name, f)
      write_entry(r'Efield[V/m]_vs_alpha[1/m]', tbl_data[:, Efield_col], tbl_data[:, alpha_col], cfg.gas_name, f)
      if (eta_col != -1):
         tbl_data[:, eta_col] = tbl_data[:, eta_col] * gas_num_dens
         write_entry(r'Efield[V/m]_vs_eta[1/m]', tbl_data[:, Efield_col], tbl_data[:, eta_col], cfg.gas_name, f)
      write_entry(r'Efield[V/m]_vs_energy[eV]', tbl_data[:, Efield_col], tbl_data[:, eV_col], cfg.gas_name, f)

def write_entry(entry_name, x_data, y_data, gas_name, f):
   f.write('\n\n' + entry_name)
   f.write('\n' + gas_name)
   f.write('\n' + 'COMMENT: generated by bolsig_convert.py')
   f.write('\n-----------------------\n')
   np.savetxt(f, np.column_stack([x_data, y_data]))
   f.write('-----------------------\n')

if __name__ == '__main__':
   convert()