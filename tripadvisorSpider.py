# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request
from tripadvisor.items import TripadvisorItem
import re
import time
import requests
from lxml import html
import json
from selenium import webdriver
import traceback
from scrapy.selector import Selector
import pandas as pd

class TripadvisorspiderSpider(scrapy.Spider):
    name = 'tripadvisorSpider'
    allowed_domains = ['tripadvisor.in']
    #start_urls = ['https://www.tripadvisor.in/Hotels-g186591-Ireland-Hotels.html']

    def __init__(self):
        self.driver = webdriver.Chrome('c:/chromedriver/chromedriver.exe')
        self.init_url = "https://www.tripadvisor.in/Hotels-g186591-Ireland-Hotels.html"
        self.headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'}
        self.lst = []
    
    def get_euro_rate(self):
        
        res = requests.get("http://www.floatrates.com/daily/inr.json", headers=self.headers)
        res_json = json.loads(res.text)
        euro_rate = round(res_json['eur']['rate'], 2)
        return euro_rate
        
    def start_requests(self):
        self.driver.get(self.init_url)
        sel = Selector(text=self.driver.page_source)
        # import pdb;pdb.set_trace()
        nodes = sel.xpath("//div[@class='prw_rup prw_meta_hsx_responsive_listing ui_section listItem']")
        for node in nodes:
            try:
                hotel_url = ''.join(node.xpath(".//a[@data-clicksource='HotelName']/@href").extract()).strip()
                absolute_url = 'https://www.tripadvisor.in' + hotel_url
                print("absolute_url", absolute_url)
                cnt = 0
                country = ''
                self.parse_hotels_html(absolute_url, cnt, country)
            except:
                print(traceback.print_exc())
                continue
            
        # Pagination
        try:
            self.driver.find_element_by_xpath("//div[@class='unified ui_pagination standard_pagination ui_section listFooter']/span[contains(text(),'Next')]").click()
        except:
            return
        time.sleep(10)
        sel_ = Selector(text=self.driver.page_source)
        cnt_ = 1
        self.driver_next_res(sel_, cnt_)
        
        # write in csv
        dynamic_file_name = time.strftime("%Y%m%d%H%M")
        df = pd.DataFrame(self.lst)
        df.to_csv("tripadvisor_"+dynamic_file_name+".csv", encoding='utf-8')
    
    
    def driver_next_res(self, sel, cnt_):
        cnt_ += 1
        print("Pagination===main======>")
        nodes = sel.xpath("//div[@class='prw_rup prw_meta_hsx_responsive_listing ui_section listItem']")
        for node in nodes:
            try:
                hotel_url = ''.join(node.xpath(".//a[@data-clicksource='HotelName']/@href").extract()).strip()
                absolute_url = 'https://www.tripadvisor.in' + hotel_url
                print("absolute_url==2===", absolute_url)
                cnt = 0
                country = ''
                self.parse_hotels_html(absolute_url, cnt, country)
            except:
                print(traceback.print_exc())
                continue
        
        # How many main page you want please define here
        
        #if cnt_ ==  28:
            #return
        
        # Pagination
        try:
            self.driver.find_element_by_xpath("//div[@class='unified ui_pagination standard_pagination ui_section listFooter']/span[contains(text(),'Next')]").click()
        except:
            return
        time.sleep(10)
        sel_ = Selector(text=self.driver.page_source)
        self.driver_next_res(sel_, cnt_)
        

    def parse_hotels_html(self, url, cnt, country):
        cnt += 1
        item = {}
        res = requests.get(url, headers = self.headers)
        response = html.fromstring(res.text)
        country_t = '|'.join(response.xpath("//li[@class='breadcrumb']//text()")).strip()
        item['country'] = ''
        if cnt == 1:
            item['country'] = country_t[country_t.rindex("|")+1:]
        else:
            item['country'] = country
        # item['country'] = ''.join(response.xpath("//h1[@class='page_h1_line1']/text()").extract()).strip() 
        # import pdb; pdb.set_trace()
        item['hotel_name'] = ''.join(response.xpath("//h1[@class='hotels-hotel-review-atf-info-parts-Heading__heading--2ZOcD']/text()")).strip()
        item['hotel_price'] = ''
        hotel_price = '|'.join(response.xpath("//div[contains(@class,'hotels-hotel-offers-DetailChevronOffer__price--py2LH')]/text()")).strip()
        if not hotel_price:
            hotel_price = '|'.join(response.xpath("//div[contains(@class,'hotels-hotel-offers-DominantOffer__price--D-ycN')]/text()")).strip()
            
        hotel_price = hotel_price.split("|")[0]
        if hotel_price:
            item['hotel_price'] = ''.join(re.findall('[0-9]',hotel_price)).strip()
            item['hotel_price'] = float(item['hotel_price']) * self.get_euro_rate()
        
        item['total_reviews'] = ''.join(response.xpath("//span[@class='hotels-hotel-review-atf-info-parts-Rating__reviewCount--1sk1X']/text()")).strip()
        if item['total_reviews']:
            item['total_reviews'] = ''.join(re.findall('[0-9]',item['total_reviews'])).strip()
        
        item['hotel_location'] = ''.join(response.xpath("//div[@class='public-business-listing-ContactInfo__offer--KAFI4 public-business-listing-ContactInfo__atfInfo--3wJ1b']//span[@class='public-business-listing-ContactInfo__ui_link--1_7Zp public-business-listing-ContactInfo__level_4--3JgmI']/text()")).strip()
        item['near_by_restaurants'] = ''.join(response.xpath("//span[@class='hotels-hotel-review-location-layout-Highlight__number--S3wsZ hotels-hotel-review-location-layout-Highlight__orange--1N-BP']/text()")).strip()
        if item['near_by_restaurants']:
            item['near_by_restaurants'] = ''.join(re.findall('[0-9]',item['near_by_restaurants'])).strip()

        item['near_by_attractions'] = ''.join(response.xpath("//span[@class='hotels-hotel-review-location-layout-Highlight__number--S3wsZ hotels-hotel-review-location-layout-Highlight__blue--2qc3K']/text()")).strip()
        if item['near_by_attractions']:
            item['near_by_attractions'] = ''.join(re.findall('[0-9]',item['near_by_attractions'])).strip()
            
        # Reviews
        review_nodes = response.xpath("//div[@class='hotels-community-tab-common-Card__card--ihfZB hotels-community-tab-common-Card__section--4r93H']")
        for review_node in review_nodes:
            item['review_title'] = ''.join(review_node.xpath(".//a[@class='location-review-review-list-parts-ReviewTitle__reviewTitleText--2tFRT']/span/span/text()")).strip()
            item['review_desc'] = ''.join(review_node.xpath(".//q[@class='location-review-review-list-parts-ExpandableReview__reviewText--gOmRC']/span/text()")).strip()
            item['review_date'] = ''.join(review_node.xpath(".//div[@class='social-member-event-MemberEventOnObjectBlock__event_type--3njyv']/span/text()")).replace("wrote a review","").strip()

            dic_ = {'country':item['country'], 'hotel_name':item['hotel_name'], 'hotel_price':item['hotel_price'],
                    'total_reviews':item['total_reviews'], 'hotel_location':item['hotel_location'],
                    'near_by_restaurants':item['near_by_restaurants'], 'near_by_attractions':item['near_by_attractions'],
                    'review_title':item['review_title'], 'review_desc':item['review_desc'], 'review_date':item['review_date']} 
            print(dic_)
            self.lst.append(dic_)
         
            
        # How many review page you want please define here
        if cnt == 20: # means 2 review page only = 10 review for each hotel
            return
        
        # Pagination
        try:
            next_page = response.xpath("//a[contains(@class,'ui_button nav next primary')]/@href")
        except:
            return
        
        if len(next_page) > 0:
            print("Next Page ============================================>")
            next_page_absolute_url = 'https://www.tripadvisor.in' + ''.join(next_page).strip()
            self.parse_hotels_html(next_page_absolute_url, cnt, item['country'])
            
    
    
