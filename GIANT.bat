@echo off
color 0A
title THE GIANT

:MENU
cls
echo.
echo  ============================================================
echo    THE GIANT - YouTube Intelligence System
echo    Phase 1  -  Discovery and Review
echo  ============================================================
echo.
echo    [1]  Run Discovery         all 20 niches automatically
echo    [2]  Custom Niche          run one niche of your choice
echo    [3]  Manual Review         open browser dashboard
echo    [4]  Database Stats        see totals and niche breakdown
echo    [5]  Reset Database        wipe everything and start fresh
echo    [6]  Exit
echo.
echo  ============================================================
echo.
set /p choice="  Enter choice (1-6): "

if "%choice%"=="1" goto DISCOVER_ALL
if "%choice%"=="2" goto DISCOVER_CUSTOM
if "%choice%"=="3" goto REVIEW
if "%choice%"=="4" goto STATS
if "%choice%"=="5" goto RESET
if "%choice%"=="6" goto EXIT
goto MENU


:DISCOVER_ALL
cls
echo.
echo  ============================================================
echo    RUNNING DISCOVERY - All 20 Niches
echo    Press Ctrl+C to stop at any time
echo  ============================================================
echo.
call venv\Scripts\activate.bat
python giant.py
echo.
echo  ============================================================
echo    Done. Go to Manual Review [3] to approve channels.
echo  ============================================================
echo.
pause
goto MENU


:DISCOVER_CUSTOM
cls
echo.
echo  ============================================================
echo    CUSTOM NICHE DISCOVERY
echo  ============================================================
echo.
set /p niche="  Enter niche name: "
echo.
call venv\Scripts\activate.bat
python giant.py --custom %niche%
echo.
echo  ============================================================
echo    Done. Go to Manual Review [3] to approve channels.
echo  ============================================================
echo.
pause
goto MENU


:REVIEW
cls
echo.
echo  ============================================================
echo    MANUAL REVIEW - Opening browser dashboard
echo    Press Ctrl+C here when done reviewing
echo  ============================================================
echo.
call venv\Scripts\activate.bat
python review.py
echo.
pause
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
    c.execute(\"SELECT COUNT(*) FROM channels WHERE is_golden=1\")
    golden = c.fetchone()[0]
    try:
        c.execute(\"SELECT COUNT(*) FROM channels WHERE review_status='pending'\")
        pending = c.fetchone()[0]
        c.execute(\"SELECT COUNT(*) FROM channels WHERE review_status='rejected'\")
        rejected = c.fetchone()[0]
    except:
        pending = rejected = 0
    c.execute('SELECT COUNT(DISTINCT niche) FROM channels')
    niches = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM keywords WHERE searched=1')
    kw_done = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM keywords')
    kw_total = c.fetchone()[0]
    print()
    print(f'  Total Channels    : {total}')
    print(f'  Golden (Approved) : {golden}')
    print(f'  Pending Review    : {pending}')
    print(f'  Rejected          : {rejected}')
    print(f'  Niches Active     : {niches}')
    print(f'  Keywords Done     : {kw_done} / {kw_total}')
    print()
    print('  ' + '-'*50)
    print(f'  {\"NICHE\":<32} {\"TOTAL\":>6}  {\"GOLDEN\":>6}')
    print('  ' + '-'*50)
    c.execute('SELECT niche, COUNT(*), SUM(CASE WHEN is_golden=1 THEN 1 ELSE 0 END) FROM channels GROUP BY niche ORDER BY COUNT(*) DESC')
    for r in c.fetchall():
        print(f'  {str(r[0]):<32} {r[1]:>6}  {(r[2] or 0):>6}')
    print()
    conn.close()
except Exception as e:
    print(f'  Error: {e}')
    print('  Run Discovery first.')
"
echo.
pause
goto MENU


:RESET
cls
echo.
echo  ============================================================
echo    RESET DATABASE
echo    WARNING: Deletes all channels and discovery data.
echo  ============================================================
echo.
set /p confirm="  Type YES to confirm: "
if /i "%confirm%"=="YES" (
    call venv\Scripts\activate.bat
    python reset_db.py
    echo.
    echo  Done. Run Discovery to start fresh.
) else (
    echo  Cancelled.
)
echo.
pause
goto MENU


:EXIT
echo.
echo  Goodbye.
echo.
timeout /t 2 >nul
exit
