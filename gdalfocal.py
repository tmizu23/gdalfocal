# -*- coding: utf-8 -*-
import os, sys, gdal, ogr, numpy,argparse
from gdalconst import *
from osgeo import osr

#x,y座標を中心とした円からx方向に1or-1移動するときの差分
def xdiff(x,y,dx):
    sum=0
    if dx == 1 or dx == -1:
        for (j,i) in zip(xlist,ylist):
            sum = sum + data[y+i][x+j*dx+dx]- data[y+i][x-j*dx]
    return sum
#x,y座標を中心とした円からy方向に1or-1移動するときの差分
def ydiff(x,y,dy):
    sum=0
    if dy == 1 or dy == -1:
        for (i,j) in zip(xlist,ylist): #i,j入れ替え
            sum = sum + data[y+i*dy+dy][x+j]- data[y-i*dy][x+j]
    return sum

#x,y座標を中心としてdist距離以下の値の合計
def focalsum(x,y,dist):
    sum=0
    row_num = int(round(-dist/y_size))
    col_num = int(round(dist/x_size))

    if (y-row_num < 0 or y+row_num >= rows or x-col_num < 0 or x+col_num >= cols):
        return ndv
    for i in range(-row_num,row_num+1):
        for j in range(-col_num,col_num+1):
            if (i*y_size)*(i*y_size)+(j*x_size)*(j*x_size) <= dist*dist:
                sum = sum + data[y+i][x+j]
    return sum

if __name__ == '__main__':
    ##
    # inputのデータ形式はFloat32だけ対応
    # フォーカル範囲内にNODATがあるものはダメ

    parser = argparse.ArgumentParser(description='This is focal statistics program.') # parserを作る
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('-nodata', type=float,default=-9999.0,help="Area's edge is nodata of this value.") # オプションを追加します
    parser.add_argument('-r', type=int,required=True,help='statistical radius by map unit') # このオプションは必須です
    parser.add_argument('-s', default='sum',type=str, choices=['sum','mean'],help='statistical type, sum or mean') # このオプションは必須です
    parser.add_argument('--version', action='version', version='%(prog)s 0.1') # version
    args = parser.parse_args()


    argvs = sys.argv
    input=args.input
    output=args.output
    dist=args.r
    statics = args.s
    ndv=args.nodata


    gdal.AllRegister()
    ds = gdal.Open(input)
    data = ds.GetRasterBand(1).ReadAsArray()
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    (upper_left_x, x_size, x_rotation, upper_left_y, y_rotation, y_size) = ds.GetGeoTransform()
    Projection = osr.SpatialReference()
    Projection.ImportFromWkt(ds.GetProjectionRef())

    outdata = numpy.empty((rows,cols))
    outdata.fill(ndv)


    row_num = int(round(-dist/y_size))
    col_num = int(round(dist/x_size))
    xlist=[]
    ylist=[]

    circlenumber = 0

    ##半円の円周部分のX,Y座標取得。円内のセル数カウント
    for i in range(-row_num,row_num+1):
        j=0
        circlenumber = circlenumber + 1
        while (i*y_size)*(i*y_size)+(j*x_size)*(j*x_size) <= dist*dist:
            j = j + 1

        circlenumber = circlenumber + (j-1)*2
        xlist.append(j-1)
        ylist.append(i)


    print "### INFO"
    print "cols_cell_count:%d" % cols
    print "rows_cell_count:%d" % rows
    print "focal_cell_count:%d" % circlenumber
    print ""

    #row_num行目をまず計算
    outdata[row_num][col_num] = focalsum(col_num,row_num,dist)

    for j in range(col_num+1, cols-col_num):
        outdata[row_num][j] = outdata[row_num][j-1] + xdiff(j-1,row_num,1)

    print "0...",
    k=0
    maxnum = (rows-row_num-row_num-1)*(cols-col_num-col_num)
    #row_num+1行目以降を計算
    for i in range(row_num+1,rows-row_num):
        for j in range(col_num, cols-col_num):
            outdata[i][j] = outdata[i-1][j]+ydiff(j,i-1,1)
            #プログレス表示
            if (100*k/maxnum) % 100 > (100*(k-1)/maxnum) % 100 and ((100*k/maxnum) % 10 == 0):
                sys.stdout.write("%d..."% ((100*k/maxnum) % 100))
            k=k+1


    #平均値を計算
    if statics == 'mean':
        for i in range(rows):
            for j in range(cols):
                if outdata[i][j] != ndv:
                    outdata[i][j]=outdata[i][j]/circlenumber


    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(output, cols, rows, 1,gdal.GDT_Float32)

    dst_ds.SetGeoTransform(ds.GetGeoTransform())
    dst_ds.SetProjection( Projection.ExportToWkt())
    dst_band = dst_ds.GetRasterBand(1)
    dst_band.WriteArray(outdata)
    dst_band.SetNoDataValue(ndv)

    dst_ds = None
    ds = None




