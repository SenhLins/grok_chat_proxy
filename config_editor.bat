@echo off
:: 设置控制台编码为UTF-8
chcp 65001 > nul

:: 设置文件名
set "filename=config.txt"

:: 检测文件是否存在
if exist "%filename%" (
    echo 检测到当前目录下已存在 %filename% 文件。
    echo.
    call :ask_confirm "是否覆盖现有文件？(Y/N)"
    if /i "%confirm%"=="n" (
        echo 已取消操作，文件未修改。
        pause
        exit /b
    )
)

:: 初始化 cookies 数组
set "cookies=["

:: 循环输入 cookie
:input_cookie
set "new_cookie="
set /p new_cookie=请输入 cookie 的内容（或直接按回车结束输入）：
if "%new_cookie%"=="" goto end_input

:: 将新 cookie 添加到 cookies 数组
if "%cookies%"=="[" (
    set "cookies=%cookies%"%new_cookie%""
) else (
    set "cookies=%cookies%, "%new_cookie%""
)

:: 询问是否继续输入
call :ask_confirm "是否继续输入下一个 cookie？(Y/N)"
if /i "%confirm%"=="n" goto end_input
goto input_cookie

:end_input
:: 完成 cookies 数组
set "cookies=%cookies%]"

:: 生成 JSON 内容并写入文件
echo {"cookies": %cookies%, "last_cookie_index": {"grok-2": 0, "grok-3": 0, "grok-3-thinking": 0}, "temporary_mode": true} > %filename%

:: 检查文件是否写入成功
if errorlevel 1 (
    echo 错误：文件写入失败！
    pause
    exit /b
)

:: 提示完成
echo.
echo 文件 %filename% 已成功创建/更新！

:: 修改文件后缀名为 .json
set "new_filename=config.json"
ren "%filename%" "%new_filename%"

:: 检查重命名是否成功
if errorlevel 1 (
    echo 错误：文件重命名失败！
    pause
    exit /b
)

echo.
echo 文件已重命名为 %new_filename%。
pause
exit /b

:: 自定义函数：通过回车确认 Y/N
:ask_confirm
set "confirm="
set /p confirm=%~1 
if "%confirm%"=="" set "confirm=y"  :: 默认回车为 Y
if /i "%confirm%"=="y" set "confirm=y"
if /i "%confirm%"=="n" set "confirm=n"
if /i "%confirm%" neq "y" if /i "%confirm%" neq "n" (
    echo 输入无效，请输入 Y 或 N。
    goto ask_confirm
)
exit /b
