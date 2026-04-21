class CONFIG:
    INDATA=r"input/dataRaw"
    INTEM=r"input/template"
    INUSER=r"input/userInput"

    OUTPUT=r"output"

    TEMPTIME=r"temp/time"
    TEMPXLSX=r"temp/XLSX"
    TEMPXLSX2=r"temp/XLSX2"

    TEMPMD=r"temp/md"
    TEMPMDJSON=r"temp/mdJSON"
    TEMPJSONTEMPLATE=r"temp/JSONtemplate"

    TEMPFILL=r"temp/fill"
    FEXTRACTIME=r"Scripts/extractTime.py"
    FCUTTIMEXLSX=r"Scripts/cutTimeXLSX.py"
    FCUTCOLUMNXLSX=r"Scripts/cutColumnXLSX.py"
    FFILLXLSX=r"Scripts/fillXLSX.py"
    FXLSX2JSON=r"Scripts/xlsx2JSON.py"

    FXLSX2JSONTEMPLATE=r"Scripts/xlsx2JSONtemplate.py"

    FD2MD=r"Scripts/d2md.py"
    FMD2JSON=r"Scripts/md2JSON.py"

    FJ2FILLJSON=r"Scripts/J2fillJ.py"

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
    # f(config.FJ2FILLJSON,config.TEMPMDJSON,config.TEMPJSONTEMPLATE,config.TEMPFILL)
    
    
    f(config.FFILLXLSX,config.TEMPFILL,config.INTEM,config.OUTPUT)
    
    
    print(f"运行时间: {time.perf_counter() - start:.6f} 秒")
    pass

def process_and_fill(data_files,
            template_file,
            requirements_file,
            output_file):
    config.INDATA=data_files
    config.INTEM=template_file
    config.INUSER=requirements_file
    config.OUTPUT=output_file
    main()

if __name__ == "__main__":
    main()