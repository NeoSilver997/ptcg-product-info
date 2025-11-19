# 日文卡片插入來源分析報告

## 已刪除的日文卡片
- **總數**: 80 張
- **ID 範圍**: 4859-4887+ (部分)
- **來源系列**: SVN (SV Night Wanderer), MA (Master Art), SV-P (SV Promotional Cards)

## 插入來源追蹤

### 1. html_to_sqlite.py
**檔案位置**: `c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\html_to_sqlite.py`

**功能**: 
- 從 `html_pages/` 資料夾讀取 HTML 檔案並解析
- 直接插入到 `cards` 資料表

**關鍵程式碼** (第 202-204 行):
```python
sql = f"INSERT INTO cards ({fields}) VALUES ({placeholders})"
conn.execute(sql, list(card_data.values()))
```

**問題分析**:
- 該腳本從官方網站爬取的 HTML 頁面中提取卡片資料
- 如果官方網站上的卡片名稱是日文（例如 SVN 系列尚未發行中文版），就會直接插入日文名稱
- 目前只有 `M1S` 系列有 92 個 HTML 檔案，但日文卡片來自其他系列

### 2. pokemon_card_scraper.py
**檔案位置**: `c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_card_scraper.py`

**功能**:
- 從 `https://asia.pokemon-card.com/hk/card-search/` 爬取卡片列表
- 下載詳細頁面到 `html_pages/` 資料夾
- 包含稀有度辨識邏輯

**可能情況**:
- 最近有人執行此腳本爬取了 SVN、MA、SV-P 等新系列
- 這些系列在香港官網上可能只有日文名稱
- 爬取後由 `html_to_sqlite.py` 插入到資料庫

### 3. csv_to_sqlite.py
**檔案位置**: `c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\csv_to_sqlite.py`

**功能**:
- 從 CSV 檔案讀取卡片資料並插入到 `card_csv` 資料表
- **不是直接插入到 `cards` 資料表**

**結論**: 此腳本不是日文卡片的插入來源

## 最可能的插入路徑

```
1. pokemon_card_scraper.py 執行
   ↓
2. 爬取 SVN/MA/SV-P 系列的頁面（這些系列官網上是日文名稱）
   ↓
3. 儲存 HTML 檔案到 html_pages/ 資料夾
   ↓
4. html_to_sqlite.py 執行
   ↓
5. 解析 HTML 並插入日文名稱到 cards 資料表
```

## 建議處理方式

### 選項 1: 修改 html_to_sqlite.py 增加名稱驗證
在插入前檢查卡片名稱是否為日文，如果是則跳過或標記為待翻譯

```python
import re

def is_japanese_name(name):
    """檢查是否包含日文片假名"""
    return bool(re.search(r'[ァ-ヺ]', name))

def insert_card(conn, card_data):
    if is_japanese_name(card_data.get('Name', '')):
        logging.warning(f"Skipping Japanese card: {card_data['Name']}")
        return
    # ... 原有插入邏輯
```

### 選項 2: 建立翻譯對照表
為常用的日文訓練家卡建立中日對照表，在插入時自動替換

### 選項 3: 只爬取已發行中文版的系列
在 `pokemon_card_scraper.py` 的 URL 中限制系列代碼，避免爬取日文限定系列

## 驗證資料

**已刪除的卡片範例**:
- ID 4859: ネストボール (巢穴球)
- ID 4860: ナンジャモ (娜娜米)
- ID 4869: ハイパーボール (大師球)
- ID 4872: ボスの指令 (老大的指令)
- ID 4887: ボウルタウン (深缽鎮) - 已手動修正

**備份檔案**:
- `pokemon_cards_backup_before_delete_20251116_012121.db`
