#!/usr/bin/python

import os
import csv
import numpy as np
import pandas as pd
from collections import Counter
from progress.bar import Bar

#define unit
scale_KB = 1000
scale_MB = 1000*1000
scale_GB = 1000*1000*1000
scale_KiB = 1024
scale_MiB = 1024*1024
scale_GiB = 1024*1024*1024

# TLC NAND 512Gb
nand_size = 512 						# Gb
nand_page_size = 8*1024		# byte
nand_page_num = 1728
nand_plane = 4		
nand_block_num = 1214

class rand_ssd :
	def __init__(self, length = 10000, payload=False, seq_unit = 0, debug=False) :
		self.count = 0
		self.length = length
		self.percent = [0.5, 0.5]
		self.values = []
		self.debug = debug
		
	def set_custom_percentage(self, percent) :
		if sum(percent) != 100 :
			print ('error : sum of percent is not 100')
		else :
			self.percent = [] 
			for value in percent :
				self.percent.append(value / 100.0)	
			if self.debug == True :
				print(self.percent)
			
	def get_value(self) :
		if len(self.values) == 0 :
			values = np.random.choice(len(self.percent), self.length, p = self.percent)
			#np.random.shuffle(value)
			self.values = list(values)
			
			#if payload == True and seq_unit > scale_MiB :
			
			if self.debug == True : 
				print('rand_ssd generate number')
				print(self.values)
			
		return self.values.pop()										
		
	def get_value2(self, value) :
		if len(self.values) == 0 :
			values = np.random.choice(len(self.percent), self.length, p = self.percent)
			self.values = list(values)
		
		# remove value form valuse[]  like pop() function
		try :
			index = self.values.index(value)
		except ValueError :
			index = 0
																
		del self.values[index]
		return value											
			
	def set_value(self, value) :
		self.values.append(value)	

	def shuffle(self) :
		np.random.shuffle(self.values)	
						
	def show_percent(self) :
		print(self.percent)		
					
	def test_value(self) :
		value = np.random.choice(len(self.percent), self.length, p = self.percent)
		print(values)
		print(Counter(values))

class ssd :
	def __init__(self, capacity=256) :
		self.capacity = capacity
		self.sector_size = 512
	
	def get_bytes_per_lba(self) :
		return self.sector_size
	
	def get_max_lba(self) :
		# unit of ssd_capacity is GB
		# unit of return value is divided by sector size
		return ((self.capacity*scale_GB) - self.sector_size) / self.sector_size
		
	def get_min_lba(self) :
		return 0
				
class statistics :
	def __init__(self, payload_size, payload_percent, workload_range, workload_percent) :
		self.sector_size = 512
		self.payload_size = payload_size
		self.payload_percent = payload_percent
		self.workload_range = workload_range
		self.workload_percent = workload_percent
		
		self.payload_count = []
		for index in range(len(self.payload_percent)) :
			self.payload_count.append(0)
			
		self.workload_count = []
		for index in range(len(self.workload_percent)) :
			self.workload_count.append(0)						
		
		self.total_write = 0
		
		#print(self.workload_range)
					
	def add_workload(self, lba, length) :
		for index, workload_range in enumerate(self.workload_range) :
			if lba >= workload_range[0] and lba <= workload_range[1] :
				self.workload_count[index] = self.workload_count[index] + 1

		for index, payload_size in enumerate(self.payload_size) :
			if length == payload_size  :
				self.payload_count[index] = self.payload_count[index] + 1
								
		self.total_write = self.total_write + 1				 
		#print('write lba = ' + str(lba) + ', length = ' + str(length))
		
	def show_result(self) :
		print('======================')
		print('statistics result')	
		print('total write : ' + str(self.total_write))
		print('write range count : ')
		print(self.workload_count)
		print('write length count : ')
		print(self.payload_count)		

class workload_temp :
	def __init__(self, section_num, max_lba) :
		self.section_num = section_num
		self.max_lba = max_lba
		self.temp_count = []
		
		for index in range(self.section_num) :
			self.temp_count.append(0)
			
		self.lba_divide = self.max_lba / self.section_num
		self.temp_sum = 0  					
		
	def add(self, lba, length) :
		index = int(lba / self.lba_divide)
		
		if length <= 8 :
			self.temp_count[index] = self.temp_count[index] + 1
		else :
			self.temp_count[index] = self.temp_count[index] + (length / 8)
		
		self.temp_sum = self.temp_sum + 1
	
	def clear(self) :
		self.temp_sum = 0
		for index in range(self.section_num) :
			self.temp_count[index] = 0														
	
	def get_count(self) :
		return self.temp_count
		
	def show_result(self) :
		print('======================')
		print('workload temperature result')
		print(self.temp_count)		
									
def TestMain(workload, payload, dst_filename, ssd_capacity=256, precondfill=100, runfill=100, repeat_cycles=3., run = False) :
	"""
	Test Main
	
	ssd_capacity : unit is GB
	precondfill : percentage value for capacity
	runfill : percentage value for capacity
	repeat_cycles : repeat count afer filling full capactity 
	run : True means runnig main workload, False means omit runnig 
	"""
	ssd_id = ssd(ssd_capacity)
	
	max_lba = ssd.get_max_lba(ssd_id) - ssd.get_min_lba(ssd_id) + 1
	lba_size = ssd.get_bytes_per_lba(ssd_id)

	# calculate total write size (unit is sector size)
	if runfill == 100 :
		max_lba_writes = int(repeat_cycles*(max_lba+1)) 
	else :
		max_lba_writes = int((max_lba+1) * runfill / 100)		
	
	lba_writes_counter = 0
	aligned_border = 4096 / lba_size

	# calculate ssd information
	nand_small_block_size = nand_page_size * nand_page_num
	nand_big_block_size = nand_small_block_size * nand_plane
	number_of_die = ssd_capacity/(nand_size/8)
	ssd_info = {
		'ssd capacity [GB]' : ssd_capacity,
		'nand capacity[Gb]' : nand_size,
		'nand small block size[MB]' : int(nand_small_block_size / scale_MB), 
		'nand big block size[MB]' : int(nand_big_block_size / scale_MB),
		'number of die' : number_of_die,
		'super block size [MB]' : int(nand_big_block_size * number_of_die / scale_MB),
		'max lba' : max_lba
	}
				
	# prepare stage										
	# convert workload from % to lba range		
	workload_range= []
	for wl_range in workload['range']  :
		workload_range.append((max_lba * wl_range[0] / 100, (max_lba * wl_range[1] - lba_size) / 100))

	#workload_range[-1] = (workload_range[-1][0], workload_range[-1][1] - payload_size[-1])
	
	# convert payload_size from bytes to lba
	payload_unit_write_size = 0
	payload_sector_num = []
	for idx, length in enumerate(payload['length']) :
		payload_sector_num.append(length / lba_size)
		payload_unit_write_size = payload_unit_write_size + (length * payload['percent'][idx])

	workload_df = pd.DataFrame(workload)
	workload_df['lba'] =pd.Series(workload_range, index=workload_df.index)			
						
	payload_df = pd.DataFrame(payload)
	payload_df['sector_num'] =pd.Series(payload_sector_num, index=payload_df.index)	

	# show enterprise workload test condition 
	ssd_info_df = pd.Series(ssd_info)
	print('ssd info :')
	print(ssd_info_df)
						
	print('\nworkload write size [GB] : ' + str(max_lba_writes*lba_size/scale_GB))		
	print('payload unit write size [KiB] :' + str(payload_unit_write_size/scale_KiB))
		
	print('\nworkload : ')
	print(workload_df)
	
	print('\npayload : ')
	print(payload_df)	
		
	# initialize rand generator	
	workload_rand = rand_ssd(10000)
	rand_ssd.set_custom_percentage(workload_rand, workload_df['percent'])
		
	payload_rand = rand_ssd(10000)
	rand_ssd.set_custom_percentage(payload_rand, payload_df['percent'])
			
	# initialize workload temperature contents
	ssd_temp = workload_temp(100, max_lba)
				
	# initialize statistics information 
	ssd_statistics = statistics(payload_sector_num, payload_df['percent'], workload_range, workload_df['percent'])
	
	# prepare the csv file for recoding workload
	if os.path.isfile(dst_filename) :
		os.remove(dst_filename)
		
	fp = open(dst_filename, 'w', encoding='utf-8')
	cvs_wr = csv.writer(fp)
	cvs_wr.writerow(['lba', 'length', 'temp'])
	
	# precondition stage
	# precondfill is percentage value, if it is 250, precond is 250% so full filling is 2 and remaining percentage is 50%
	if precondfill > 0 :
		print('\n\nprecondition start...')
		precond_chunk_size = 128
		count_full_filling = int(precondfill / 100)
		partial_filling_percent = int(precondfill % 100)		
		for unused in range(count_full_filling) :
			print('precondition fill 100%')
			#precondition.FillCard(0, precond_chunk_size, 100)
		if partial_filling_percent > 0 :
			print('precondition fill' + str(partial_filling_percent) + '%')
			#precondition.FillCard(0, precond_chunk_size, partial_filling_percent)
			
		print('precondition end...')	
	else :
		print('\nprecondition skip...')
				
	if run == True :
		print('\n\nrun JEDEC219a enterprise workload...')		
		
		#main stage
		with Bar('Progressing', max = 100) as bar :
			progress_save = 0
			
			payload_num = 0
			while lba_writes_counter < max_lba_writes :
				if payload_num == 0 : 
					chunk_idx = rand_ssd.get_value(payload_rand)									
					range_idx = rand_ssd.get_value(workload_rand)
					lba = np.random.randint(workload_range[range_idx][0], workload_range[range_idx][1])
					payload_num = payload['seq'][chunk_idx] * scale_KiB / payload['length'] [chunk_idx]				
				else :
					chunk_idx = rand_ssd.get_value2(payload_rand, prev_chunk_idx)
					if payload['seq_lba'] == True :
						range_idx = rand_ssd.get_value(workload_rand)
						lba = prev_lba + payload_sector_num[chunk_idx]
					else :
						range_idx = rand_ssd.get_value2(workload_rand, prev_range_idx)
						lba = np.random.randint(workload_range[range_idx][0], workload_range[range_idx][1])
																
				length = payload_sector_num[chunk_idx]
				if length >= aligned_border :
					lba = (lba / aligned_border) * aligned_border
			
				#Adapter.Write(lba, length)		
				#print('write lba = ' + str(lba) + ', length = ' + str(length))
				if length == 8 and range_idx == 0:
					temp_value = 1
				else :
					temp_value = 0
				
				cvs_wr.writerow([lba, length, temp_value])
			
				lba_writes_counter += length
						
				# update workload temperature
				workload_temp.add(ssd_temp, lba, length)		
						
				# update statistics
				statistics.add_workload(ssd_statistics, lba, length)
			
				progress = int((lba_writes_counter / max_lba_writes) * 100)
				if progress_save != progress :
					progress_save = progress
					bar.next()

				# check sequence and setup loop			
				if payload_num > 0 :
					prev_chunk_idx = chunk_idx
					prev_range_idx = range_idx
					prev_lba = lba
					payload_num = payload_num - 1
					if payload_num == 0:
						rand_ssd.shuffle(payload_rand)
																		
		print('end test...\n\n')
		
	# close csv file 		
	fp.close()
	
	# show workload temperature
	workload_temp.show_result(ssd_temp)
	
	# show the statics result			
	statistics.show_result(ssd_statistics)		
						
if __name__=='__main__' :

	workload = {
		'range' : [(0, 5), (5, 20), (20, 100)],
		'percent' : (50, 30, 20)
	}

	payload0 = {
		'length' : [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 8192, 16384, 32768, 65536],
		'percent' :  [4, 1, 1, 1, 1, 1, 1, 67, 10, 7, 3, 3],
		'seq' : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
		'seq_lba' : False
	}
	
	payload1 = {
		'length' : [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 8192, 16384, 32768, 65536],
		'percent' :  [4, 1, 1, 1, 1, 1, 1, 67, 10, 7, 3, 3],
		'seq' : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 256, 256],
		'seq_lba' : False
	}

	payload2 = {
		'length' : [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 8192, 16384, 32768, 65536],
		'percent' :  [4, 1, 1, 1, 1, 1, 1, 67, 10, 7, 3, 3],
		'seq' : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 256, 256],
		'seq_lba' : True
	}
																							
	#TestMain(workload, payload0, 'ssd_jedec219a.csv', 128, 0, 2, 1, True)
	#TestMain(workload, payload1, 'ssd_jedec219a_1.csv', 128, 0, 2, 1, True)
	TestMain(workload, payload2, 'ssd_jedec219a_2.csv', 128, 0, 2, 1, True)
					
