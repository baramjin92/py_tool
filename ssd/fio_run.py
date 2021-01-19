#!/usr/bin/python

import sys
import subprocess as sub
import time
import datetime
import numpy as np
import pandas as pd
import re

device = 'nvme0n1'

def exec_command(command, log=False) :
	if log is True :
		print('exec_command : ', command)

	p = sub.Popen(command, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
	p_out, p_err = p.communicate()
	rc = p.wait()
	
	return [rc, p_out, p_err]
				
def get_disksize() :
	if sys.platform == 'win32' :
		rc, p_out, p_err = exec_command('wmic diskdrive where "Index=%s" get size /format:csv', 0)	# 0 -> dut
		p_out = re.sub('\r', ' ', p_out).splitlines()
		
		if len(p_out) > 2:
			full_size = int(p_out[2].split(',')[-1])
			
		#dut_path = "\\\.\PhysicalDrive"
		#dut = dut_path + "%s" % dut	
	else :
		dut = '/dev/nvme0n1'
		m = re.match(r'/dev/(sd[a-z]|nvme\d+n1)$', dut)
		if not m :
			raise ValueError('Device path dose not match known case') 
		rc, p_out, p_err = exec_command("lsblk -b -drno SIZE %s" % dut )
		full_size = int(p_out.strip())
		
		return full_size

def get_ioengine() :
	if sys.platform == 'win32' :
		command = " --ioengine=windowsaio"
	else :
		command = " --ioengine=libaio"
		
	return command

def run_secure_erase() :
	if sys.platform == 'win32' :
		print('\n[secure erase] is not support')
	else : 
		print('\nRun [secure erase]')
			
	return 1

def run_fio(fio_runtime, fio_ramptime, fio_size, loops, run_type, read_ratio, block_size, io_depth, num_jobs, thread = 1) :

	if run_type == 'readwrite' :
		pattern = 'seq'
	else :
		pattern = 'rnd'
	output_format = "minimal"

	fio_ramptime = str(fio_ramptime)	
	run_type = str(run_type)
	read_ratio = str(read_ratio)
	block_size = str(block_size)
	io_depth = str(io_depth)
	num_jobs = str(num_jobs)
	
	# Make a command string
	command = "sudo fio --name=temp-fio" \
								+ " --filename=/dev/" + device \
								+ get_ioengine() \
								+ " --direct=1" \
								+ " --ramp_time=" + fio_ramptime \
								+ " --size=" + str(fio_size) \
								+ " --rw=" + run_type \
								+ " --rwmixread=" + read_ratio \
								+ " --bs=" + block_size + " --iodepth=" + io_depth \
								+ " --numjobs=" + num_jobs \
								+ " --group_reporting --output=/home/fioresult.txt"													
																																										
	if fio_runtime > 0 :
		command += " --time_based --runtime=" + str(fio_runtime)
	else :
		if loops <= 0 :
			loops = 1
		if pattern == 'seq' :
			command += " --loops=" + str(loops)
		else :						
			io_limit = int(fio_size * loops / thread)			# fio follows size basically, in order to make a loop, need to set io_limit
			command += " --io_limit=" + str(io_limit)							

	if output_format == 'minimal' :
		command += " --minimal"
	else :
		command += " --output-format=" + output_format
																
	print(command)
				
	sys.stdout.flush()
				
	# Run command string in the shell
	#output = sub.call(command, shell=True)
	
	return 1

def convert_time_to_sec(time) :
	if 'hours' in time :
		time = time.replace('hours', '')
		time = int(time) * 3600
	elif 'mins' in time :
		time = time.replace('mins', '')
		time = int(time) * 60
	else : 
		time = int(time)
	
	return time

def convert_size_unit(value) :
	if 'KB' in value :
		value = value.replace('KB', '')
		value = int(value) * 1024
	elif 'MB' in value :
		value = value.replace('MB', '')
		value = int(value) * 1024 *1024
	elif 'GB' in value :
		value = value.replace('GB', '')
		value = int(value) * 1024 *1024*1024		
	else :
		value = int(value)		

	return(value)	

def performance_test() :

	# rw option
	rw_template = {'SW' : 'readwrite', 'SR' : 'readwrite', 'RW' : 'randwrite', 'RR' : 'randread'}
				
	# load excel file for performance test
	df = pd.read_excel('SSD - Performance Measurement.xlsx')

	print('\nRun profile ...')		
	print(df)

	key = df.columns
	#for index in range(len(df)) :
	for index in range(8) :
		print("\nStart : " + df.loc[index, key[0]])
	
		run_type = df.loc[index, key[1]]
		rw = rw_template[run_type]
		
		run_time = df.loc[index, key[2]]
		if run_time is not np.nan :
			run_time = convert_time_to_sec(run_time)
		else : 
			run_time = 0
		
		ramp_time = df.loc[index, key[3]]
		ramp_time = int(ramp_time)
		
		loops = df.loc[index, key[4]]
		loops = int(loops)
		block_size = df.loc[index, key[5]]
		block_size = convert_size_unit(block_size)
		
		fio_size = df.loc[index, key[6]]
		if fio_size == 'Full' :
			#fio_size = get_disksize()
			#fio_szie = str(fio_size)
			fio_size = 128*1024*1024*1024
		else :
			fio_size = convert_size_unit(fio_size)
			
		write_ratio = df.loc[index, key[8]]
		read_ratio = 100 - int(write_ratio)
		
		io_depth = df.loc[index, key[9]]
		num_jobs = df.loc[index, key[10]]
		
		#print(run_type + ":" + str(run_time) + ":" + str(block_size) )
		# run_fio require run_time, ramp_time, fio_size, run_type, read_ratio, block_size, io_depth, num_jobs  
		run_fio(run_time, ramp_time, fio_size, loops, rw, read_ratio, block_size, io_depth, num_jobs)
									
	return 1

def main() :
		
	for run in ('randwrite', 'randread', 'readwrite') :
		blocksize = '4096'
		for numjobs in (1, 4, 8) :
			for iodepth in (1, 4, 8, 16) :
				run_fio(60, 0, "1G", run, 70, blocksize, iodepth, numjobs)
	return 1				
			
if __name__ == '__main__' :
	exec_command('ls', True)
	
	# show performance test spec
	print('SSD Perfomenace Measurement Test')
	print('Start time : ' + str(datetime.datetime.now()))
	
	run_secure_erase()
	performance_test()		
	# main()
			