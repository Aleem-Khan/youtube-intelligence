@echo off
color 0A
title THE GIANT — YouTube Intelligence System

:MENU
cls
echo.
echo  ============================================================
echo    THE GIANT — YouTube Intelligence System
echo    Multi-Niche Channel Discovery and Pattern Intelligence
echo  ============================================================
echo.
echo    [1]  Run Discovery         find new channels for any niche
echo    [2]  Extract Patterns      analyze title and thumbnail formulas
echo    [3]  Open Dashboard        view all data in browser
echo    [4]  Database Stats        see what you have collected
echo    [5]  Push to GitHub        update live dashboard on Vercel
echo    [6]  Exit
echo.
echo  ============================================================
echo.
set /p choice="  Enter your choice (1-6): "

if "%choice%"=="1" goto DISCOVER
if "%choice%"=="2" goto PATTERNS
if "%choice%"=="3" goto DASHBOARD
if "%choice%"=="4" goto STATS
if "%choice%"=="5" goto PUSH
if "%choice%"=="6" goto EXIT
goto MENU


:DISCOVER
cls
echo.
echo  ============================================================
echo    CHANNEL DISCOVERY
echo    Type your niche when asked. The system will generate
echo    300 keywords and search YouTube automatically.
echo  ============================================================
echo.
call venv\Scripts\activate.bat
python giant.py
echo.
echo  ============================================================
echo    Discovery finished. Press any key to return to menu.
echo  ============================================================
pause >nul
goto MENU


:PATTERNS
cls
echo.
echo  ============================================================
echo    PATTERN INTELLIGENCE ENGINE
echo    Fetches video titles from your golden channels.
echo    Uses AI to extract title formulas and thumbnail styles.
echo    Run this after discovery to build your pattern database.
echo  ============================================================
echo.
call venv\Scripts\activate.bat
python pattern_engine.py
echo.
echo  ============================================================
echo    Pattern extraction done. Press any key to return.
echo  ============================================================
pause >nul
goto MENU


:DASHBOARD
cls
echo.
echo  ============================================================
echo    OPENING DASHBOARD
echo  ============================================================
echo.
call venv\Scripts\activate.bat
python viewer.py
echo.
echo  Opening in browser...
start viewer.html
echo.
echo  Press any key to return to menu.
pause >nul
goto MENU


:STATS
cls
echo.
echo  ============================================================
echo    DATABASE STATS
echo  ============================================================
echo.
call venv\Scripts\activate.bat
python -c "
import sqlite3
try:
    conn = sqlite3.connect('intelligence.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM channels')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM channels WHERE is_golden=1')
    golden = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT niche) FROM channels')
    niches = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM keywords')
    kw = c.fetchone()[0]
    try:
        c.execute('SELECT COUNT(*) FROM channel_titles')
        titles = c.fetchone()[0]
    except:
        titles = 0
    try:
        c.execute('SELECT COUNT(*) FROM title_patterns')
        tp = c.fetchone()[0]
    except:
        tp = 0
    try:
        c.execute('SELECT COUNT(*) FROM thumbnail_patterns')
        thp = c.fetchone()[0]
    except:
        thp = 0
    print()
    print(f'  Total Channels        : {total}')
    print(f'  Golden Channels       : {golden}')
    print(f'  Niches Researched     : {niches}')
    print(f'  Keywords in Database  : {kw}')
    print(f'  Titles Collected      : {titles}')
    print(f'  Title Patterns        : {tp}')
    print(f'  Thumbnail Patterns    : {thp}')
    print()
    c.execute('SELECT niche, COUNT(*), SUM(is_golden) FROM channels GROUP BY niche ORDER BY SUM(is_golden) DESC')
    rows = c.fetchall()
    sep = '-' * 52
    print(f'  {sep}')
    print(f'  NICHE                            CHANNELS   GOLDEN')
    print(f'  {sep}')
    for r in rows:
        print(f'  {r[0]:<32} {r[1]:>8} {r[2]:>8}')
    print()
    conn.close()
except Exception as e:
    print(f'  Error: {e}')
    print('  Run discovery first.')
"
echo.
echo  ============================================================
echo  Press any key to return to menu.
pause >nul
goto MENU


:PUSH
cls
echo.
echo  ============================================================
echo    PUSH TO GITHUB — Update Live Dashboard on Vercel
echo  ============================================================
echo.
echo  Step 1: Regenerating dashboard...
call venv\Scripts\activate.bat
python viewer.py
echo.
echo  Step 2: Pushing to GitHub...
git add index.html
git commit -m "dashboard update %date% %time%"
git push origin main
echo.
echo  ============================================================
echo  Done! Your live Vercel dashboard has been updated.
echo  Visit your Vercel URL to see the latest data.
echo  ============================================================
echo.
pause >nul
goto MENU


:EXIT
cls
echo.
echo  THE GIANT is shutting down.
echo.
timeout /t 2 >nul
exit
