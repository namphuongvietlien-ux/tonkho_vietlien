@echo off
REM Script tự động add, commit và push lên git

REM Kiểm tra trạng thái git

git status

REM Add tất cả thay đổi
git add .

REM Commit với message mặc định
git commit -m "Auto commit by script"

REM Push lên nhánh hiện tại
git push

pause