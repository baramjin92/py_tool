#!/usr/bin/python

import numpy as np
import numpy_financial as npf

import pandas as pd
import pandas_datareader.data as web

#import request
from urllib.request import urlopen
from bs4 import BeautifulSoup
from tabulate import tabulate

import time
import datetime 

LOG_ENABLE = False

ROE_1ST_PRIORITY = 0
ROE_CONSENSUS = 1
ROE_WEIGHTED_MEAN = 2
ROE_RECENT = 3
ROE_SEPERATE = 4

def log_print(str) :
	if LOG_ENABLE == True :
		print(str)

class report() :
	def __init__(self) :
		self.report_str = ''
		
	def print(self, str) :
		self.report_str = self.report_str + str + '\n'
		
	def show(self) :
		print(self.report_str)	

def calculate_rim_data(stockcode, roe_option = ROE_1ST_PRIORITY, report_show = False) :	
	rep = report()

	stock_code = 'A%06d'%stockcode

	url = "http://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=%s&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701"%stock_code
	html = urlopen(url)
	#html = urlopen("http://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A005930&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701")
	#html = urlopen("http://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A005930&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701")	
		
	#bsObject = BeautifulSoup(html, "html.parser")
	bsObject = BeautifulSoup(html, "lxml")
	
	table = bsObject.find_all('table')
	#Load all table once'
	df = pd.read_html(str(table))

	'''
	# Reference Data
	# 연결-연관, 연결-분기, 별도-분기
	table_index = [11, 12, 15]
	'
	for i in table_index :
		print('\ntable %d'%(i))
		print(tabulate(df[i], headers = 'keys', tablefmt='psq'))		

	#accounting = df[11]
	#print(accounting)	
	#print(accounting.index)
	#print(accounting.columns)
	#print(accounting.loc[17, [('Annual', '2015/12'), ('Annual', '2017/12')]])
	'''

	company_name = bsObject.find('h1', {'id':'giName'})
	rep.print('----------')
	rep.print(company_name.text)
	rep.print('----------')

	# 시세현황
	company_value = df[0]
	#print(company_value)
	
	# 종가
	name = company_value.iloc[0,0]
	if name.find('종가') >= 0 :
		price = company_value.iloc[0,1]
		closing_price, net_change = price.split('/')
		rep.print('종가 : ' + closing_price + ' 전일대비 : ' + net_change)
	else :
		rep.print('cannot find closing price')
		
	# 베타
	name = company_value.iloc[3,2]
	if name.find('베타') >= 0 :
		beta = float(company_value.iloc[3,3])
		rep.print(name + ' : %f'%beta)
	else :
		rep.print('cannot find beta')
		
	# 발행 주식수
	name = company_value.iloc[6,0]
	if name.find('발행주식수') >= 0 :
		share_outstanding = company_value.iloc[6,1]
		common_stock, preferred_stock = share_outstanding.split('/')
		common_stock = common_stock.replace(',', '', 10)
		preferred_stock = preferred_stock.replace(',', '', 10)
		total_stock = int(common_stock) + int(preferred_stock)
		rep.print('보통주 : ' + common_stock + ' 우선주 : ' + preferred_stock)
		rep.print('발행주식수 : %d'%total_stock)
	else :
		rep.print('cannot find share outstanding')
						
	# 주주구분 현황
	owner = df[4]
	#print(owner)
	
	# 자기 주식 (자사주 + 자사주 신탁)
	rs_index = 4
	name = owner.iloc[rs_index,0]
	if np.isnan(owner.iloc[rs_index,1]) == True :
		reacquired_stock = 0
	else :
		reacquired_stock = owner.iloc[rs_index,1]
	rep.print(name + ' : %d'%reacquired_stock)

	rep.print('----------')				
	# PER, 12M PER, 업종 PER, EV/EBITDA, PBR, 배당 수익률
	for corp_group2 in bsObject.find_all('div', {'class':'corp_group2'}) : 
		h_per = corp_group2.select('dl > dd')[1].text
		h_12m = corp_group2.select('dl > dd')[3].text
		h_u_per = corp_group2.select('dl > dd')[5].text	
		h_pbr = corp_group2.select('dl > dd')[7].text
		h_rate = corp_group2.select('dl > dd')[9].text
	
		rep.print('PER : ' + h_per) 
		rep.print('12M PER : ' + h_12m)
		rep.print('업종 PER : ' + h_u_per)
		rep.print('PBR : ' + h_pbr)
		rep.print('배당 수익률 : ' + h_rate)
	
	#EV/EBITDA
	compare_value = df[9]

	ev_index = 5
	name = compare_value.iloc[ev_index, 0]	
	if name.find('EV/EBITDA') >= 0 :
		ev_ebitda = company_value.iloc[ev_index, 1]
		if np.isnan(ev_ebitda) == True :
			rep.print(name + ' : Nan')
		else :
			rep.print(name + ' : %f'%ev_ebitda)
	else :
		rep.print('cannot find EV/EBITDA')
		
	rep.print('----------')
	# 별도 요구 수익률 (required_rate_of_return)
	additional_rrr = True
	if additional_rrr == True :
		final_apply_discount_rate = 7.86		# 최종 적용 할인률
	else :
		risk_free_rate = 1.52								# 무위험 이자율
		market_risk_premium = 6.57				# 시장 위험 프리미엄	

		final_apply_discount_rate = risk_free_rate + market_risk_premium * beta
	
	rep.print('최종 적용 할인률 : %f %%'%final_apply_discount_rate)
	
	#
	# 연결 회계 (consolidate  accounting - quarter)
	#
	accounting = df[12]
	# DEBUG START
	if False :
		rows = len(accounting)
		cols = len(accounting.columns)
		print('행 : %d, 열 : %d'%(rows, cols))
		#print(tabulate(accounting, headers = 'keys', tablefmt='psq'))		
		print(accounting)
		print(accounting.columns)
	# DEBUG END
		
	# columns format is ('Net Quarter', 'year/month')
	recent_quarter = accounting.columns[5]
	recent_year, recent_month = recent_quarter[1].split('/')
	recent_month = int(recent_month)
	
	# 매출액(0)과 지배주주지분(9) 사이의 최소값
	sale_index = 0
	profit_index = 4
	share_index = 9
	
	rep.print('----------')
	rep.print(str(accounting.iloc[[sale_index, profit_index, share_index], 1:len(accounting.columns)]))
	rep.print('----------')	
	min_sales = accounting.iloc[sale_index, 1:6].min()
	min_shares = accounting.iloc[share_index, 1:6].min()
	#mean_shares = accounting.iloc[share_index, 1:6].mean()
	mean_shares = (accounting.iloc[share_index, 1] + accounting.iloc[share_index, 5])/2
	rep.print('최소 매출액 : %d, 최소 지배주주지분 : %d, 평균 지배주주지분(0, 5) : %f'%(min_sales, min_shares, mean_shares))
	min_0_9 = min(min_sales, min_shares)
	# 지배주주 순이익(4)의 4분기 합
	sum_4_quarters = accounting.iloc[profit_index, 2:6].sum()
	rep.print('4분기 지배주주 순이익 합: %d'%sum_4_quarters)
	
	if min_0_9 == 0 :
		rate1 = mean_shares / min_0_9
	else :
		rate1 = float(sum_4_quarters) / mean_shares
	rate1 = rate1 * 100		
	rep.print('Rate1 : %f %%'%rate1)
		
	#		
	# 별도 회계 (seperated accounting - quater)
	#
	accounting = df[15]

	sale_index = 0
	profit_index = 3
	interest_index = 6

	rep.print('----------')
	rep.print(str(accounting.iloc[[sale_index, profit_index, interest_index], 1:len(accounting.columns)]))
	rep.print('----------')
	# 매출액(0)과 자본총계(6) 사이의 최소값
	min_seperated_sales = accounting.iloc[sale_index, 1:6].min()
	min_total_ownership_interest = accounting.iloc[interest_index, 1:6].min()
	mean_total_ownership_interest = (accounting.iloc[interest_index, 1] + accounting.iloc[interest_index, 5])/2
	rep.print('최소 매출액 : %d, 최소 자본총계 : %d, 평균 자본총계(0,5) : %d'%(min_seperated_sales, min_total_ownership_interest, mean_total_ownership_interest))
	min_0_6 = min(min_seperated_sales, min_total_ownership_interest)
	# 당기 순이익(3)의 4분기 합	
	sum_4_quarters1 = accounting.iloc[profit_index, 2:6].sum()
	rep.print('4분기 당기 순이익 합 : %d'%sum_4_quarters1)
	
	rate2 = sum_4_quarters1 / mean_total_ownership_interest
	rate2 = rate2 * 100
	rep.print('Rate2 : %f %%'%rate2)
	
	if np.isnan(rate1) == True :
		if min_0_6 == 0 :
			final_rate = 0
		else :
			final_rate = rate2
	else :
		final_rate = rate1	
																									
	# 연결 회계 (consolidate  accounting - annual)
	accounting = df[11]
	
	profit_index = 4
	share_index = 9
	roe_index = 17
	
	max_cols = len(accounting.columns)
	date = accounting.columns[1]
	year, month = date[1].split('/')
	year = int(year)
	month = int(month)
		
	years = range(year, year + max_cols-1)
			
	rep.print('----------')
	rep.print(str(accounting.iloc[[roe_index, share_index, profit_index], 1:len(accounting.columns)]))
	rep.print('----------')
	if accounting.iloc[share_index, 0].find('지배주주지분') >= 0 and accounting.iloc[roe_index, 0].find('ROE') >= 0 :
		controlling_share_holder_net_profits = accounting.iloc[profit_index, 1:max_cols]
		controlling_shareholder_shares = accounting.iloc[share_index, 1:max_cols]
		roes = accounting.iloc[roe_index, 1:max_cols]
		
	# 추세 판정
	trend = None
	if final_rate == 0 :
		if roes[3] < roes[2] and roes[4] < roes[3] :
			trend = 'downturn'
		elif roes[3] > roes[2] and roes[4] > roes[3] :
			trend = 'upturn'			
	else :
		if roes[3] < roes[2] and final_rate < roes[3] :
			trend = 'downturn'			
		elif roes[3] > roes[2] and final_rate > roes[3] :
			trend = 'upturn'			

	# 가중 평균
	if final_rate == 0 :
		weighted_mean = (roes[4]*3 + roes[3]*2+roes[2]) / 6
	else :
		if (recent_month % 12) == 0 :
			weighted_mean = (roes[4]*3 + roes[3]*2+roes[2]) / 6
		else :
			L21 = (recent_month % 12) / 6
			M21 = L21 + 4
			weighted_mean = (final_rate*3 + roes[4]*L21 + roes[3]) / M21				

	# 1순위 
	if roes[7] > 0 :
		first_priority = roes[7]
	elif roes[6] > 0 :
		first_priority = roes[6]
	elif roes[5] > 0 :
		first_priority = roes[5]
	elif  final_rate > 0 :
		if trend == 'upturn' or trend == 'downturn' :
			first_priority = final_rate
		else :
			first_priority = weighted_mean
	else :
		first_priority = 3
		rep.print('can not find first rank')
	
	rep.print('컨센서스 : %f %%, 가중 평균 : %f %%, 1순위 : %f %% 최근 : %f %%'%(roes[7], weighted_mean, first_priority, final_rate))

	# 자기자본 이익률(ROE : Return On Equity) 추정		
	if roe_option == ROE_1ST_PRIORITY :
		roe_estimation = first_priority
	if roe_option == ROE_CONSENSUS :
		roe_estimation = roes[7]
	if roe_option == ROE_WEIGHTED_MEAN :
		roe_estimation = weighted_mean
	if roe_option == ROE_RECENT :
		roe_estimation = final_rate
	if roe_option == ROE_SEPERATE :
		roe_estimation = 10
		
	roe_estimation = first_priority

	ref_year = years[4]
	ref_controlling_shareholder_share = controlling_shareholder_shares[4]
	for index, value in enumerate(roes) :
		if roe_estimation == value :
			ref_year = years[index]
			ref_controlling_shareholder_share = controlling_shareholder_shares[index]
			break

	rep.print('----------')										
	rep.print('분석 기준 시점 : %d, 기준시점 주주지분 : %d'%(ref_year, ref_controlling_shareholder_share))		
	
	today = datetime.datetime.today()
	day = datetime.datetime(ref_year, 12, 31)  - today
																			
	# 초과이익 지속 계수
	excess_earning_rate_constant = [1.0, 0.9, 0.8]
	results = []
	for rate_constant in excess_earning_rate_constant :
		excess_earning_rate = roe_estimation - final_apply_discount_rate
		roe = final_apply_discount_rate + excess_earning_rate
		share = ref_controlling_shareholder_share
		years = range(ref_year+1, ref_year+10)	

		rep.print('----------')
		rep.print('%d, %f %%, %f %% %f 억, %f 억, %d 억'%(ref_year, excess_earning_rate, roe, 0, share, 0))

		ex_earnings = []
		for index, year in enumerate(years) :
			excess_earning_rate = excess_earning_rate * rate_constant
			roe = final_apply_discount_rate + excess_earning_rate
			net_profit = share * (roe / 100)
			share1 = share + net_profit
			excess_earning = net_profit - share *  (final_apply_discount_rate / 100)
			ex_earnings.append(excess_earning)
			rep.print('%d, %f %%, %f %% %f 억, %f 억, %d 억'%(year, excess_earning_rate, roe, net_profit, share1, excess_earning))
			share = share1
		
		net_present_value = npf.npv(final_apply_discount_rate / 100, ex_earnings)
		ref_shareholder_performance = ref_controlling_shareholder_share + net_present_value
		optimal_stock_price = ref_shareholder_performance * 100000000 / (total_stock + reacquired_stock)
		cur_shareholder_performance = ref_shareholder_performance / ((1+final_apply_discount_rate / 100) ** (day.days / 365))
		cur_optimal_stock_price = optimal_stock_price / ((1+final_apply_discount_rate / 100) ** (day.days / 365))
		
		rep.print('PV of RI : %f'%net_present_value)
		rep.print('[분석시점 기준] 주주가치 : %f 억, 적정주가 : %f'%(ref_shareholder_performance, optimal_stock_price))
		rep.print('[현재 기준] 주주가치 : %f 억, 적정주가 : %f'%(cur_shareholder_performance, cur_optimal_stock_price))

		results.append([optimal_stock_price, cur_optimal_stock_price])

	if report_show == True:
		rep.show()	
						
	return company_name.text, closing_price, results 		
												
def save_stock_code() :
	print('get stock code form kind.krx.co.kr')
	
	url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
	html = urlopen(url)
	
	bsObject = BeautifulSoup(html, 'html.parser')
	table = bsObject.find_all('table')

	df = pd.read_html(str(table), header=0)[0]	
	#df = pd.read_html(url, header=0)[0]

	df.iloc[:, [0,1]].to_csv('stock_code.csv')

	return df.iloc[:, [0,1]]
				
def load_stock_code() :
	try :
		df = pd.read_csv('stock_code.csv')
	except :
		print('cannot load stock_code.csv')
		df = save_stock_code()
		
	return df				
			
'''
	Test kind.krx.co.kr
	종목 코드를 얻기 위하여 접속하여 정보 다운로드 여부 확인
'''					
def test() :
	# 'kosdaq'
	# &marketType=kosdaqMkt
	# 'kospi'
	# &marketType=stockMkt
	url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
	df = pd.read_html(url, header=0)[0]

	print(df.head())
	print(df.tail())

'''
	Test comp.fnguide.com
	재무 정보를 얻기 위하여 comp.fnguide.com을 접근하여 table 정보를 얻어오는 과정 테스트
'''													
def test2() :
	stock_code = 'A005930'
	url = "http://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=%s&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701"%stock_code
	html = urlopen(url)
	#html = urlopen("http://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A005930&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701")
	#html = urlopen("http://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A005930&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701")	
		
	#bsObject = BeautifulSoup(html, "html.parser")
	bsObject = BeautifulSoup(html, "lxml")
	
	table = bsObject.find_all('table')
	df = pd.read_html(str(table), header=0)

	company_name = bsObject.find('h1', {'id':'giName'})
	print(company_name.text)

	print('----------')
	# 시세현황
	company_value = df[11]
	
	print(company_value)
	print(company_value.index)
	print(company_value.columns)

'''
	Test comp.fnguide.com
	재무 정보를 얻기 위하여 comp.fnguide.com을 접근하여 table 정보를 얻어오는 과정 테스트
'''
def test_fnguide() :
	html = urlopen("http://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A058470&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701")
	#html = urlopen("http://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A005930&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701")	
		
	#bsObject = BeautifulSoup(html, "html.parser")
	bsObject = BeautifulSoup(html, "lxml")
	
	#print(bsObject)
	company_name = bsObject.find('h1', {'id':'giName'})
	print(company_name.text)

	for corp_group2 in bsObject.find_all('div', {'class':'corp_group2'}) : 
		h_per = corp_group2.select('dl > dd')[1].text
		h_12m = corp_group2.select('dl > dd')[3].text
		h_u_per = corp_group2.select('dl > dd')[5].text	
		h_pbr = corp_group2.select('dl > dd')[7].text
		h_rate = corp_group2.select('dl > dd')[9].text
	
		print(h_per) 
		print(h_12m)
		print(h_u_per)
		print(h_pbr)
		print(h_rate)

'''
	Test DataReader
	DataReader 를 이용하여 yahoo로부터 주가 정보 얻어오는 것을 테스트
'''													
def test3(stockcode) :
	start = datetime.datetime(2020, 6, 1)
	end = datetime.datetime(2020, 6, 30)
	
	stock = '%06d.KS'%stockcode
	gs = web.DataReader(stock, 'yahoo', start, end)
	#gs = web.DataReader(['AAPL', '078930.KS'], 'yahoo', start, end)
	
	print(gs)				
		
	#plt.plot(gs['Adj Close'])
	#plt.show()											

def test_rim() :
	df = load_stock_code()	
		
	name = '일진머티리얼즈'
	stockcode = df['종목코드'][df['회사명'] == name]
					
	name, closing_price, results = calculate_rim_data('A%06d'%stockcode, ROE_1ST_PRIORITY)

RIM_ENABLE = True
STOCK_PRICE_ENABLE = False
UNIT_TEST_ENABLE = True																																
																						
if __name__=='__main__':	
	df = load_stock_code()

	if RIM_ENABLE == True :
						
		#print(df[df['회사명'] == '리노공업'].index.values)
		#print(df[df['회사명'] == '삼성'])
		#print(df.head())
		
		start_time = time.time()
		
		#name = input('회사명 : ')
		#names = ['아이에스동서', '와이엠티']'
		#names = ['이오테크닉스', '씨젠', '리노공업', '기가레인']
		#name = 'DB하이텍'
		#name = '미코'
		#name = '동구바이오제약'
		names = ['솔브레인홀딩스']
		names = ['호텔신라']
		
		for name in names : 
			try :
				stockcode = df['종목코드'][df['회사명'] == name]
				
				name, closing_price, results = calculate_rim_data(stockcode, report_show = True)
				print('%s : %s, %s'%(name, closing_price, str(results)))
			except :					
				print('error is occurred') 
		
	if STOCK_PRICE_ENABLE == True :
		print('==========')	
		test3(stockcode)

	if UNIT_TEST_ENABLE == True :
		print('==========')					
				
		#test_fnguide()