import sys
import time

import pandas as pd
import socketio

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

# 獲取命令行參數中的起始查詢地號
if len(sys.argv) > 1:
    symbol_no = int(sys.argv[1])
else:
    symbol_no = int(input("請輸入起始的查詢地號: "))

# 初始化 WebDriver
options = Options()
options.add_argument('--headless') #啟動無頭模式
webdriver_path = '/usr/local/bin/chromedriver'
service = Service(webdriver_path)
driver = webdriver.Chrome(service=service, options=options)

# 初始化 SocketIO
sio = socketio.Client()
sio.connect('http://localhost:5000')

# 打開目標網頁
driver.get('https://landuse.tycg.gov.tw/sys/QueryProgress/QueryProgress.aspx')

# 初始化資料儲存結構
data = []

try:
    while True:
        # 1. 選擇年份（預設113年）
        select_year = Select(driver.find_element(By.ID, 'ContentPlaceHolder1_ddl_Year1'))
        select_year.select_by_value('113')
        time.sleep(1)

        # 2. 輸入文號
        symbol_no_input = driver.find_element(By.ID, 'tb_SymbolNo')
        symbol_no_input.clear()
        symbol_no_input.send_keys(str(symbol_no))
        time.sleep(1)

        # 3. 點擊查詢按鈕
        query_button = driver.find_element(By.ID, 'ContentPlaceHolder1_btn_Query1')
        query_button.click()
        time.sleep(3)

        try:
            # 4. 檢查是否有結果
            symbol_link = driver.find_element(By.ID, 'ContentPlaceHolder1_gv_Progress_hl_SymbolNo_0')
            symbol_text = symbol_link.text

            # 5. 爬取申請日期
            apply_date = driver.find_element(By.ID, 'ContentPlaceHolder1_gv_Progress_lbl_ApplyDate_0').text

            # 6. 點擊文號連結
            symbol_link.click()
            time.sleep(3)

            # 切換到浮動視窗
            driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, '#cboxLoadedContent iframe'))

            # 7. 爬取申請人姓名
            applicant_name = driver.find_element(By.CSS_SELECTOR, '#form1 > div:nth-child(3) > table:nth-child(1) > tbody > tr:nth-child(2) > td').text

            # 8. 爬取區域
            district = driver.find_element(By.CSS_SELECTOR, '#form1 > div:nth-child(3) > table:nth-child(2) > tbody > tr:nth-child(2) > td').text

            # 9. 爬取段名
            section_name = driver.find_element(By.CSS_SELECTOR, '#form1 > div:nth-child(3) > table:nth-child(2) > tbody > tr:nth-child(3) > td').text

            # 10. 爬取所有地號（最後一筆不爬取）
            land_rows = driver.find_elements(By.CSS_SELECTOR, '#gv_ApplyLand > tbody > tr')
            for i in range(1, len(land_rows) - 1):
                land_number = driver.find_element(By.CSS_SELECTOR, f'#gv_ApplyLand > tbody > tr:nth-child({i + 1}) > td:nth-child(2)').text
                # 將資料儲存到列表中
                data.append([symbol_text, applicant_name, district, section_name, land_number, apply_date])

                # 即時顯示爬取的結果
                result = f"爬取結果: {symbol_text}, {applicant_name}, {district}, {section_name}, {land_number}, {apply_date}"
                print(result)
                sio.emit('scrape_update', result)

            # 回到主頁面
            driver.switch_to.default_content()
            driver.back()
            time.sleep(3)

            # 增加文號
            symbol_no += 1
        except NoSuchElementException:
            # 發送沒有查詢結果的訊息給前端
            sio.emit('scrape_update', '查詢結束或查無結果。')
            break

finally:
    # 關閉瀏覽器
    driver.quit()

# 將資料寫入到 Excel
if data:
    df = pd.DataFrame(data, columns=['本案文號', '申請人姓名', '區名稱', '地段名稱', '申請地號', '申請日期'])
    df.to_excel('output.xlsx', index=False)
    print("資料已儲存至 output.xlsx")
    # 發送檔案儲存完成的訊息
    if sio.connected:
        sio.emit('scrape_complete', '資料已儲存至 output.xlsx')
        time.sleep(3)
    else:
        print("SocketIO 未連接，無法發送 'scrape_complete' 訊息")
sio.disconnect()