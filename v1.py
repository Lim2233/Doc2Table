class CONFIG:
    #文件夹
    INDATA=r"StreamTry/v1/input/dataRaw"
    INTEM=r"StreamTry/v1/input/template"
    INUSER=r"StreamTry/v1/input/userInput"
    
    OUTPUT=r"StreamTry/v1/output"
    
    TEMPTIME=r"StreamTry/v1/temp/time"
    TEMPXLSX=r"StreamTry/v1/temp/XLSX"
    TEMPXLSX2=r"StreamTry/v1/temp/XLSX2"
    
    TEMPMD=r"StreamTry/v1/temp/md"
    TEMPMDJSON=r"StreamTry/v1/temp/mdJSON"
    TEMPJSONTEMPLATE=r"StreamTry/v1/temp/JSONtemplate"
    
        
    TEMPFILL=r"StreamTry/v1/temp/fill"
    #脚本
    FEXTRACTIME=r"StreamTry/v1/Scripts/extractTime.py"
    FCUTTIMEXLSX=r"StreamTry/v1/Scripts/cutTimeXLSX.py"
    FCUTCOLUMNXLSX=r"StreamTry/v1/Scripts/cutColumnXLSX.py"
    FFILLXLSX=r"StreamTry/v1/Scripts/fillXLSX.py"
    FXLSX2JSON=r"StreamTry/v1/Scripts/xlsx2JSON.py"
    
    FXLSX2JSONTEMPLATE=r"StreamTry/v1/Scripts/xlsx2JSONtemplate.py"
    
    FD2MD=r"StreamTry/v1/Scripts/d2md.py"
    FMD2JSON=r"StreamTry/v1/Scripts/md2JSON.py"
    
    FJ2FILLJSON=r"StreamTry/v1/Scripts/J2fillJ.py"
    
    pass

config= CONFIG()

import os
import time

def f(*args: str):
    os.system("python " + " ".join(args))

def main():
    
    start = time.perf_counter()
    f(config.FEXTRACTIME,config.INUSER,config.TEMPTIME)
    f(config.FCUTTIMEXLSX,config.INDATA,config.TEMPTIME,config.TEMPXLSX)
    f(config.FCUTCOLUMNXLSX,config.TEMPXLSX,config.INTEM,config.TEMPXLSX2)
    f(config.FXLSX2JSON,config.TEMPXLSX2,config.TEMPFILL)
    
    f(config.FD2MD,config.INDATA,config.TEMPMD)
    f(config.FMD2JSON,config.TEMPMD,config.TEMPMDJSON)
    f(config.FXLSX2JSONTEMPLATE,config.INTEM,config.TEMPJSONTEMPLATE)
    f(config.FJ2FILLJSON,config.TEMPMDJSON,config.TEMPJSONTEMPLATE,config.TEMPFILL)
    
    
    f(config.FFILLXLSX,config.TEMPFILL,config.INTEM,config.OUTPUT)
    
    
    print(f"运行时间: {time.perf_counter() - start:.6f} 秒")
    pass


if __name__ == "__main__":
    main()