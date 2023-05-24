from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import pandas as pd
import time
import csv
import sys
import numpy as np
import re

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_teachingbooks(path):

    start = time.time()
    print('-'*75)
    print('Scraping teachingbooks.net ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'teachingbooks_data.xlsx'
        # getting the books under each category
        links = []
        nbooks, npages = 0, 0
        homepage = 'https://www.teachingbooks.net/tb.cgi?keywordType1=title&adv=title&go=1'
        driver.get(homepage)
        while True:           
            # scraping books urls
            titles = wait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.book--card-contain")))
            for title in titles:
                try:
                    nbooks += 1
                    print(f'Scraping the url for book {nbooks}')
                    link = wait(title, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                    links.append(link)
                except Exception as err:
                    print('The below error occurred during the scraping from teachingbooks.com, retrying ..')
                    print('-'*50)
                    print(err)
                    continue

            # checking the next page
            try:
                li = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.page-item")))[-1]
                button = wait(li, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.sr-only")))
                text = button.get_attribute('textContent')
                if 'Next Page' in text:
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(5)
                else:
                    break
            except:
                break
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('teachingbooks_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('teachingbooks_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')

            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')               
                
            details['Title'] = title
            details['Title Link'] = title_link                          
            # Author and author link
            author, author_link = '', ''
            try:
                h6 = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h6.author")))
                a = wait(h6, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))[0]
                author = a.get_attribute('textContent').replace('\n', '').strip().title() 
                author_link = a.get_attribute('href')
                if 'aid=' not in author_link:
                    author_link = ''
                    author = ''
            except:
                pass
                    
            details['Author'] = author            
            details['Author Link'] = author_link            

            # total resouces & awards
            resources, awards = '', ''
            try:
                tags = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.open-resources")))
                for tag in tags:
                    text = tag.get_attribute('textContent').strip()
                    if "Total Resource" in text:
                        resources = text.split(' ')[0]
                    elif "Award" in text:
                        awards = text.split(' ')[0]
            except:
                pass          
                
            details['Total Resources'] = resources 
            details['Awards'] = awards               
            
            # grade & genre & cultural experience
            grade, genre, culture = '', '', ''
            try:
                ul = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.genre.btn-list")))
                lis = wait(ul, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "li")))
                genre_found, culture_found = False, False
                for j, li in enumerate(lis):
                    text = li.get_attribute('textContent').strip()
                    if "Grade" in text:
                        grade = lis[j+1].get_attribute('textContent').strip()
                        continue
                    elif "Genre" in text:
                        genre_found = True
                        if culture_found:
                            culture_found = False
                        continue
                    elif "Cultural Experience" in text:
                        culture_found = True
                        if genre_found:
                            genre_found = False
                        continue

                    if genre_found:
                        genre += text + ', ' 
                    elif culture_found:
                        culture += text + ', '
            except:
                pass          
                
            details['Grade'] = grade 
            details['Genre'] = genre[:-2]              
            details['Cultural Experience'] = culture[:-2]              
            
            # other info
            date, count, lexile, ATOS, quiz, points = '', '', '', '', '', ''
            try:
                div = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.col-10.col-md-6.col-lg-4")))[0]
                text = div.get_attribute('textContent').strip()
                info = text.split('\n')
                for j, elem in enumerate(info):
                    if "Year Published" in elem:
                        date = elem.replace("Year Published", "").strip()
                    elif "Word Count" in elem:
                        count = elem.replace("Word Count", "").strip().replace(',', '')
                    elif "Lexile Level:" in elem:
                        lexile = elem.replace("Lexile Level:", "").strip()
                    elif "ATOS Reading Level:" in elem:
                        ATOS = elem.replace("ATOS Reading Level:", "").strip()
                    elif "AR Point" in elem:
                        elem = elem.replace(",", "")
                        nums = re.findall("[0-9\.]+", elem)
                        if len(nums) == 2:
                            quiz = nums[0]
                            points = nums[1]
            except:
                pass          
                
            details['Publication Date'] = date 
            details['Word Count'] = count 
            details['Lexile Level'] = lexile 
            details['ATOS Level'] = ATOS 
            details['Quiz Number'] = quiz 
            details['Quiz AR Points'] = points 
                                   
            # appending the output to the datafame        
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except:
            pass

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'teachingbooks.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_teachingbooks(path)

