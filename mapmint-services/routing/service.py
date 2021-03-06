# -*- coding: utf-8 -*-
###############################################################################
#  Author:   Gérald Fenoy, gerald.fenoy@cartoworks.com
#  Copyright (c) 2010-2014, Cartoworks Inc. 
############################################################################### 
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
# 
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
# 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
################################################################################
import psycopg2
import sys
import json
import time
import authenticate.service as auth
import zoo

#CREATE TEMPORARY TABLE home_catchment10km AS SELECT * from vertices_tmp as nodes JOIN (SELECT * FROM driving_distance('SELECT gid AS id,source,target,reverse_cost as cost from ways',2000,100000,false,false)) as Goo ON nodes.id=Goo.vertex_id;

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

#con=psycopg2.connect("dbname=demogis user=djay host=127.0.0.1 port=5432")
#con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

table="network_20130318"
the_geom="wkb_geometry"

def parseDb(dbp):
    print >> sys.stderr,auth.parseDb(dbp)
    return auth.parseDb(dbp)

def reverseGeocode(conf,inputs,outputs):
    import shortInteger
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    print >> sys.stderr,"OK"
    try:
        sql="with index_query as (  select    *, st_distance(wkb_geometry, ST_Transform('SRID=4326;POINT("+inputs["x"]["value"]+" "+inputs["y"]["value"]+")',900914)) as distance  from adresse   order by wkb_geometry <-> ST_Transform('SRID=4326;POINT("+inputs["x"]["value"]+" "+inputs["y"]["value"]+")',900914) limit 100) select id, numero||' '||nom_voie||', '||code_insee||' '||(select nom from commune where code_insee=index_query.code_insee),ST_AsGeoJSON(st_transform(wkb_geometry,4326)) from index_query order by distance limit 1;"

        #sql="select id,numero||' '||nom_voie||', '||code_insee||' '||(select nom from commune where code_insee=foo1.code_insee),ST_AsGeoJSON(st_transform(wkb_geometry,4326)) from (SELECT * from (select * from adresse where wkb_geometry && ST_Buffer(ST_Transform(setSRID(GeometryFromText('POINT("+inputs["x"]["value"]+" "+inputs["y"]["value"]+")'),4326),900914),75)) As foo ORDER BY foo.wkb_geometry <-> ST_Transform(setSRID(GeometryFromText('POINT("+inputs["x"]["value"]+" "+inputs["y"]["value"]+")'),4326),900914) desc limit 5) as foo1"
        cur.execute(sql)
        res=cur.fetchall()
        outputs["Result"]["value"]=""
        fres=[]
        for i in res:
            fres+=[{"id": i[0],"label": i[1],"geometry": i[2]}]
        if len(fres)==0:
            sql="select id,numero ,ST_AsGeoJSON(st_transform(ST_Centroid(wkb_geometry),4326)) from (SELECT * from (select * from route where numero not like 'NC' AND wkb_geometry && ST_Buffer(ST_Transform(setSRID(GeometryFromText('POINT("+inputs["x"]["value"]+" "+inputs["y"]["value"]+")'),4326),900914),150)) As foo ORDER BY foo.wkb_geometry <-> ST_Transform(setSRID(GeometryFromText('POINT("+inputs["x"]["value"]+" "+inputs["y"]["value"]+")'),4326),900914) desc limit 5) as foo1"
            cur.execute(sql)
            res=cur.fetchall()
            outputs["Result"]["value"]=""
            fres=[]
            for i in res:
                fres+=[{"id": i[0],"label": i[1],"geometry": i[2]}]


        outputs["Result"]["value"]=json.dumps(fres);
        return zoo.SERVICE_SUCCEEDED
    except Exception,e:
        conf["lenv"]["message"]="Error running sql query: "+str(e)
        return zoo.SERVICE_FAILED


def geocodeAdresse(conf,inputs,outputs):
    import shortInteger
    print >> sys.stderr,"OK"
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    print >> sys.stderr,"OK"
    cur=conn.cursor()
    print >> sys.stderr,"OK"
    print >> sys.stderr,"INPUTS: "+str(inputs)
    try:
        sql="select distinct on (nom_voie) id ,nom_voie, ST_AsGeoJson(ST_Transform(wkb_geometry,4326)) from adresse where lower(numero||' '||nom_voie) like '%"+inputs["search"]["value"]+"%';"
        cur.execute(sql)
        res=cur.fetchall()
        result=[]
        for i in res:
            result+=[{"id": i[0],"label": i[1],"geometry": json.loads(i[2])}];
        outputs["Result"]["value"]=json.dumps(result)
        return zoo.SERVICE_SUCCEEDED
    except Exception,e:
        conf["lenv"]["message"]="Error running sql query: "+str(e)
        return zoo.SERVICE_FAILED    

    return zoo.SERVICE_SUCCEEDED

def loadRoute(conf,inputs,outputs):
    import shortInteger
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    sql="SELECT n, ST_AsGeoJSON(ST_GeometryN(the_geom, n)) As geomewkt FROM ((select wkb_geometry from velo.savedpath where trace='"+inputs["trace"]["value"]+"')) As foo(the_geom) CROSS JOIN generate_series(1,100) n WHERE n <= ST_NumGeometries(the_geom)"
    cur.execute(sql)
    res=cur.fetchall()
    points=[]
    j=0
    for i in res:
        print >> sys.stderr,i
        points+=[json.loads(i[1])]
        j+=1

    outputs["Result"]["value"]=json.dumps({'trace': shortInteger.unShortURL(conf,inputs["trace"]["value"]), 'points': points})
    return zoo.SERVICE_SUCCEEDED

def removeRoute(conf,inputs,outputs):
    import os
    try:
        os.remove(conf["main"]["dataPath"]+"/Paths/Saved_Result_"+inputs["trace"]["value"]+".map")
        os.remove(conf["main"]["dataPath"]+"/Paths/Saved_ZOO_DATA_Result_"+inputs["trace"]["value"]+".json")
    except Exception,e:
        print >> sys.stderr,e
    res=[]
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    sql="delete from velo.savedpath where id_user=(SELECT id from velo.users where login='"+conf["senv"]["login"]+"') and trace='"+inputs["trace"]["value"]+"'"
    cur.execute(sql)
    conn.commit()
    listRoute(conf,inputs,outputs)
    return zoo.SERVICE_SUCCEEDED

def listRoute(conf,inputs,outputs):
    res=[]
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    sql="SELECT trace,name from velo.savedpath where id_user=(SELECT id from velo.users where login='"+conf["senv"]["login"]+"')"
    cur.execute(sql)
    res=cur.fetchall()
    outputs["Result"]["value"]=json.dumps(res)
    return zoo.SERVICE_SUCCEEDED

def listRouteCG56(conf,inputs,outputs):
    res=[]
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    sql="SELECT trace,name from velo.savedpath where id_user in (SELECT id from velo.users where s_group_id=2)"
    cur.execute(sql)
    res=cur.fetchall()
    outputs["Result"]["value"]=json.dumps(res)
    return zoo.SERVICE_SUCCEEDED

def listPOIUser(conf,inputs,outputs):
    res=[]
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    sql="SELECT id,title,content,ST_AsgeoJSON(geom) from actualites where cat="+inputs["type"]["value"]
    cur.execute(sql)
    res=cur.fetchall()
    outputs["Result"]["value"]=json.dumps(res)
    return zoo.SERVICE_SUCCEEDED

def getGroupForUser(conf):
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    sql="SELECT name from velo.groups where id=(select id_group from velo.users,user_group where velo.users.id=id_user and login='"+conf["senv"]["login"]+"')"
    cur.execute(sql)
    res=cur.fetchall()
    return res[0][0]

def applyStyleToRouteMap(conf,inputs,outputs):
    import mapscript
    m0=mapscript.mapObj(inputs["map"]["value"])
    m=mapscript.mapObj(conf["main"]["dataPath"]+"/maps/project_StyleRoute.map")
    m.getLayer(0).name=m0.getLayer(0).name
    m.getLayer(0).data=m0.getLayer(0).data
    m.getLayer(0).connection=None
    m.getLayer(0).connection=m0.getLayer(0).connection
    m.getLayer(0).connectiontype=m0.getLayer(0).connectiontype
    m.getLayer(0).setProjection(m0.getLayer(0).getProjection())
    for i in range(0,m.getLayer(0).numclasses):
        if m.getLayer(0).getClass(i).name=="(null)":
            m.getLayer(0).getClass(i).name=""
            tstr=m.getLayer(0).getClass(18).getExpressionString()
            m.getLayer(0).getClass(i).setExpression("("+m.getLayer(0).getClass(18).getExpressionString().replace("(null)","")+" or "+tstr.replace("(null)","Inconnu")+")")
    m.save(inputs["map"]["value"])
    outputs["Result"]["value"]=zoo._("Map updated")
    return zoo.SERVICE_SUCCEEDED

def savePOIUser(conf,inputs,outputs):
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    inputs["title"]["value"]=inputs["title"]["value"].replace("'","''")
    inputs["content"]["value"]=inputs["content"]["value"].replace("'","''")
    if inputs.has_key("point") and inputs["point"]["value"]!="NULL":
        points="(SELECT setSRID(GeometryFromText('POINT("+inputs["point"]["value"].replace(","," ")+")'),4326) as geom)"
        print >> sys.stderr,points
        cur.execute("INSERT INTO actualites (title,content,id_user,cat,type_incident,geom) VALUES ('"+inputs["title"]["value"]+"','"+inputs["content"]["value"]+"',(SELECT id from velo.users where login='"+conf["senv"]["login"]+"'),"+inputs["type"]["value"]+","+inputs["type_incident"]["value"]+",("+points+"))")
    else:
        cur.execute("INSERT INTO actualites (title,content,id_user,lon,lat,cat,type_incident) VALUES ('"+inputs["title"]["value"]+"','"+inputs["content"]["value"]+"',(SELECT id from velo.users where login='"+conf["senv"]["login"]+"'),"+inputs["long"]["value"]+","+inputs["lat"]["value"]+","+inputs["type"]["value"]+","+inputs["type_incident"]["value"]+")")
    conn.commit()
    print >> sys.stderr,"DEBUG"
    #print >> sys.stderr,inputs["point"]["value"]
    
    outputs["Result"]["value"]=zoo._("Your news was successfully inserted.")
    return zoo.SERVICE_SUCCEEDED
    

def saveRoute(conf,inputs,outputs):
    import shutil
    import mapscript
    import shortuuid
    import shortInteger
    # Store a copy of the result then return it URL to be shared
    oFile=inputs["url"]["value"].replace(conf["main"]["mapserverAddress"]+"?map=","")
    nameId=oFile.replace(conf["main"]["dataPath"],"").replace(".map","").replace("Result_","").replace("/","")
    newNameId=str(time.time()).split('.')[0]
    shutil.copy2(oFile,oFile.replace("Result_"+nameId,"Saved_Result_"+newNameId).replace(conf["main"]["dataPath"],conf["main"]["dataPath"]+"/Paths/"))
    shutil.copy2(oFile.replace("Result_","ZOO_DATA_Result_").replace(".map",".json"),oFile.replace("Result_"+nameId,"Saved_ZOO_DATA_Result_"+newNameId).replace(".map",".json").replace(conf["main"]["dataPath"],conf["main"]["dataPath"]+"/Paths/"))
    m=mapscript.mapObj(oFile.replace("Result_"+nameId,"Paths/Saved_Result_"+newNameId))
    con1=m.getLayer(0).connection
    m.getLayer(0).connection=con1.replace("ZOO_DATA_Result_"+nameId,"Paths/Saved_ZOO_DATA_Result_"+newNameId)
    m.save(oFile.replace("Result_"+nameId,"Paths/Saved_Result_"+newNameId))

    fn=oFile.replace("Result_"+nameId,"Paths/Saved_Result_"+newNameId)
    file=open(fn,"r")
    fileo=open(fn.replace(newNameId,newNameId+"_tmp"),"w")
    for i in file.readlines():
        if i.count("EXTENT")==0:
            fileo.write(i+"\n")
    file.close()
    fileo.close()
    
    m=mapscript.mapObj(fn.replace(newNameId,newNameId+"_tmp"))
    m.save(fn)

    outputs["Result"]["value"]=conf["main"]["applicationAddress"]+"load/"+conf["senv"]["last_map"]+"/"+shortInteger.shortURL(int(newNameId))

    return zoo.SERVICE_SUCCEEDED

def saveRouteForUser(conf,inputs,outputs):
    print >> sys.stderr,"DEBUG 0000"
    saveRoute(conf,inputs,outputs)

    print >> sys.stderr,"DEBUG"
    idtrace=outputs["Result"]["value"].replace(conf["main"]["applicationAddress"]+"load/"+conf["senv"]["last_map"]+"/","")
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    points="select ST_Union(t.geom) from ("
    for i in inputs["point"]["value"]:
        if points!="select ST_Union(t.geom) from (":
            points+=" UNION "
        points+="(SELECT setSRID(GeometryFromText('POINT("+i.replace(","," ")+")'),4326) as geom)"
    points+=") as t"
    print >> sys.stderr,points
    if inputs.has_key("user"):
        cur.execute("INSERT INTO velo.savedpath (trace,name,id_user,wkb_geometry) VALUES ('"+idtrace+"','"+inputs["name"]["value"]+"',NULL,("+points+"))")
    else:
        cur.execute("INSERT INTO velo.savedpath (trace,name,id_user,wkb_geometry) VALUES ('"+idtrace+"','"+inputs["name"]["value"]+"',(SELECT id from velo.users where login='"+conf["senv"]["login"]+"'),("+points+"))")
    conn.commit()
    print >> sys.stderr,"DEBUG"
    print >> sys.stderr,inputs["point"]["value"]
    
    outputs["Result"]["value"]
    return zoo.SERVICE_SUCCEEDED

def saveContext(conf,inputs,outputs):
    import shortInteger,time,sqlite3
    print >> sys.stderr,"DEBUG 0000"
    conn = sqlite3.connect(conf['main']['dblink'])
    cur = conn.cursor()
    newNameId=str(time.time()).split('.')[0]
    name=shortInteger.shortURL(int(newNameId))
    layers=""
    if inputs["layers"].has_key('length'):
        for i in inputs["layers"]["value"]:
            if layers!='':
                layers+=","
            layers+=i
    else:
            layers+=inputs["layers"]["value"]
    req="INSERT INTO contexts (name,layers,ext) VALUES ('"+name+"','"+layers+"','"+inputs["extent"]["value"]+"')"
    print >> sys.stderr,req
    cur.execute(req)
    conn.commit()
    outputs["Result"]["value"]=conf["main"]["applicationAddress"]+"public/"+conf["senv"]["last_map"]+";c="+name
    return zoo.SERVICE_SUCCEEDED

def loadContext(conf,inputs,outputs):
    import shortInteger,time,sqlite3
    conn = sqlite3.connect(conf['main']['dblink'])
    cur = conn.cursor()
    name=inputs["name"]["value"]
    req="SELECT ext,layers from contexts where name = '"+name+"'"
    cur.execute(req)
    conn.commit()
    res=cur.fetchall()
    outputs["Result"]["value"]=json.dumps({"ext": res[0][0],"layers": res[0][1].split(',')})
    return zoo.SERVICE_SUCCEEDED

def toLon(x):
    if x > 180:
        lon = x - 360
    else:
        lon = x
    return lon

# use the vincenty formula to get accurate distance measurements
def sphereDistance(from_point, to_point):
    distance.VincentyDistance.ELLIPSOID = 'WGS-84'
    return distance.distance((toLon(from_point.x), from_point.y), \
                             (toLon(to_point.x), to_point.y))

def computeDistanceAlongLine(conf,inputs,outputs):
    import osgeo.ogr
    import osgeo.gdal
    import os
    import shapely
    import shapely.wkt
    geom=osgeo.ogr.CreateGeometryFromJson(inputs["line"]["value"])
    points=geom.GetPoints()
    res=[]
    for i in range(0,len(points)-1):
        poi0=osgeo.ogr.CreateGeometryFromWkt('POINT('+str(points[i][0])+'  '+str(points[i][1]) +')')
        poi1=osgeo.ogr.CreateGeometryFromWkt('POINT('+str(points[i+1][0])+'  '+str(points[i+1][1]) +')')

        print >> sys.stderr,dir(poi0.Distance(poi1))
        res+=[poi0.Distance(poi1)]
    outputs["Result"]["value"]=json.dumps(res)
    drv = osgeo.ogr.GetDriverByName( "GeoJSON" )
    ds = drv.CreateDataSource( "/vsimem//store"+conf["lenv"]["sid"]+"0.json" )
    lyr = ds.CreateLayer( "Result", None, osgeo.ogr.wkbUnknown )
    field_defn = osgeo.ogr.FieldDefn( "distance", osgeo.ogr.OFTString )
    field_defn.SetWidth( len(outputs["Result"]["value"]) )
    lyr.CreateField ( field_defn )
    feat = osgeo.ogr.Feature(lyr.GetLayerDefn())
    feat.SetField( "distance",outputs["Result"]["value"] )
    feat.SetGeometry(geom)
    lyr.CreateFeature(feat)
    ds.Destroy()
    print >> sys.stderr,"OK1"
    vsiFile=osgeo.gdal.VSIFOpenL("/vsimem//store"+conf["lenv"]["sid"]+"0.json","r")
    print >> sys.stderr,"OK2"
    i=0
    print >> sys.stderr,str(vsiFile)
    osgeo.gdal.VSIFSeekL(vsiFile,0,os.SEEK_END)
    print >> sys.stderr,"OK"
    while osgeo.gdal.VSIFSeekL(vsiFile,0,os.SEEK_END)>0:
        print >> sys.stderr,"OK"
        i+=1
    print >> sys.stderr,"OK"
    fileSize=osgeo.gdal.VSIFTellL(vsiFile)
    print >> sys.stderr,"OK"
    osgeo.gdal.VSIFSeekL(vsiFile,0,os.SEEK_SET)
    outputs["Result"]["value"]=osgeo.gdal.VSIFReadL(fileSize,1,vsiFile)
    osgeo.gdal.Unlink("/vsimem/store"+conf["lenv"]["sid"]+"0.json")
    print >> sys.stderr,outputs["Result"]["value"]
    return zoo.SERVICE_SUCCEEDED

def splitLine(conf,inputs,outputs):
    import osgeo.ogr
    import shapely
    import shapely.wkt
    geom=osgeo.ogr.CreateGeometryFromJson(inputs["line"]["value"]).ExportToWkt()
    sPc=inputs["startPoint"]["value"].split(",")
    sP=shapely.wkt.loads('POINT('+sPc[0]+' '+sPc[1]+')')
    ePc=inputs["endPoint"]["value"].split(",")
    eP=shapely.wkt.loads('POINT('+ePc[0]+' '+ePc[1]+')')
    line=shapely.wkt.loads(geom)
    coords = list(line.coords)
    sIdx=0
    eIdx=0
    min=line.project(sP)
    max=line.project(eP)
    if min >= max:
        _min=min
        min=max
        max=_min
    print >> sys.stderr,str(min)+" "+str(max)
    for i, p in enumerate(coords):
        pd = line.project(shapely.geometry.Point(p))
        if pd == min:
            sIdx=i
        if pd == max:
            eIdx=i
            break
    geom=osgeo.ogr.CreateGeometryFromWkt(shapely.geometry.LineString(line.coords[sIdx:eIdx]).wkt)
    outputs["Result"]["value"]=geom.ExportToJson()
    return zoo.SERVICE_SUCCEEDED
    

def findNearestNode(cur,lonlat):
    sql="with index_query as (  select    *, st_distance(the_geom,'SRID=4326;POINT("+lonlat[0]+" "+lonlat[1]+")') as distance  from vertices_tmp where the_geom && ST_Buffer(GeometryFromText('POINT("+lonlat[0]+" "+lonlat[1]+")',4326),0.001) limit 10) select * from index_query order by distance limit 1;"
    #sql="select *, distance("+the_geom+",GeometryFromText('POINT("+lonlat[0]+" "+lonlat[1]+")',4326)) as distance from vertices_tmp where ST_Intersects("+the_geom+",ST_Buffer(GeometryFromText('POINT("+lonlat[0]+" "+lonlat[1]+")',4326),0.001)) order by "+the_geom+" <-> GeometryFromText('POINT("+lonlat[0]+" "+lonlat[1]+")',4326) limit 1;"
    cur.execute(sql)
    res=cur.fetchall()
    return {"gid": res[0][0], "the_geom": res[0][1]}

def doDDPoints(conf,inputs,outputs):
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
    cur=conn.cursor()
    inputs["startPoint"]["value"]=inputs["startPoint"]["value"].split(",")
    startNode=findNearestNode(cur,inputs["startPoint"]["value"])
    sql="CREATE TEMPORARY TABLE dd_res"+conf["senv"]["MMID"]+" AS SELECT * from vertices_tmp as nodes JOIN (SELECT * FROM driving_distance('SELECT gid AS id,source,target,cost from "+table+"',"+str(startNode["gid"])+","+inputs["distance"]["value"]+",false,false)) as Goo ON nodes.id=Goo.vertex_id;"
    cur.execute(sql)
    sql="SELECT id, ST_AsGeoJSON(the_geom) FROM dd_res"+conf["senv"]["MMID"]
    cur.execute(sql)
    res=cur.fetchall()
    result={"type": "FeatureCollection","features":[]}
    for i in res:
        result["features"]+=[{"type":"Feature","geometry":json.loads(i[1]),"crs":{"type":"EPSG","properties":{"code":"4326"}}, "properties": {"id":i[0]} }]
    outputs["Result"]["value"]=json.dumps(result)
    return zoo.SERVICE_SUCCEEDED

#demogis=# select points_as_polygon('SELECT id, ST_X(the_geom) AS x, ST_Y(the_geom) AS y FROM home_catchment10km where cost < 1500');
def doDDPolygon(conf,inputs,outputs):
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
    cur=conn.cursor()
    inputs["startPoint"]["value"]=inputs["startPoint"]["value"].split(",")
    startNode=findNearestNode(cur,inputs["startPoint"]["value"])
    sql="CREATE TEMPORARY TABLE dd_res"+conf["senv"]["MMID"]+" AS SELECT * from vertices_tmp as nodes JOIN (SELECT * FROM driving_distance('SELECT gid AS id,source,target,cost from "+table+"',"+str(startNode["gid"])+","+inputs["distance"]["value"]+",false,false)) as Goo ON nodes.id=Goo.vertex_id;"
    cur.execute(sql)
    sql="select 1, ST_AsGeoJSON(the_geom) from points_as_polygon('SELECT id, ST_X(the_geom) AS x, ST_Y(the_geom) AS y FROM dd_res"+conf["senv"]["MMID"]+" where cost < "+inputs["distance"]["value"]+"');"
    cur.execute(sql)
    res=cur.fetchall()
    result={"type": "FeatureCollection","features":[]}
    for i in res:
        result["features"]+=[{"type":"Feature","geometry":json.loads(i[1]),"crs":{"type":"EPSG","properties":{"code":"4326"}}, "properties": {"id":i[0]} }]
    outputs["Result"]["value"]=json.dumps(result)
    conn.close()
    return zoo.SERVICE_SUCCEEDED
    
def findNearestEdge(cur,lonlat):
    sql="with index_query as (  select    gid, source, target, "+the_geom+", st_distance("+the_geom+", 'SRID=4326;POINT("+lonlat[0]+" "+lonlat[1]+")') as distance  from "+table+" WHERE "+the_geom+" && setsrid('BOX3D("+str(float(lonlat[0])-0.001)+" "+str(float(lonlat[1])-0.001)+", "+str(float(lonlat[0])+0.001)+" "+str(float(lonlat[1])+0.001)+")'::box3d, 4326) limit 5) select * from index_query order by distance limit 1;"
    #sql="SELECT gid, source, target, "+"+the_geom+"+", distance("+"+the_geom+"+", GeometryFromText('POINT("+lonlat[0]+" "+lonlat[1]+")' , 4326)) AS dist FROM "+table+" WHERE "+"+the_geom+"+" && setsrid('BOX3D("+str(float(lonlat[0])-0.001)+" "+str(float(lonlat[1])-0.001)+", "+str(float(lonlat[0])+0.001)+" "+str(float(lonlat[1])+0.001)+")'::box3d, 4326) ORDER BY dist LIMIT 1"
    print >> sys.stderr,"DEBUG MSG: "+str(sql)
    cur.execute(sql)
    res=cur.fetchall()
    print >> sys.stderr,"DEBUG MSG: "+str(res)
    return {"gid": res[0][0], "source": res[0][1], "target": res[0][2], "the_geom": res[0][3]}

def computeRoute(cur,startEdge,endEdge,method,conf,inputs):
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    if conf["senv"].has_key("toLoad"):
        del(conf["senv"]["toLoad"])
    if method=='SPA' :
        _sql="SELECT rt.gid, ST_AsGeoJSON(rt.the_geom) AS geojson, "+table+".name, ST_length(rt.the_geom) AS length, "+table+".gid FROM "+table+", (SELECT gid, the_geom FROM astar_sp_delta('"+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",0.01)) as rt WHERE "+table+".gid=rt.gid;"
    else:
        if inputs.has_key("distance") and inputs["distance"]["value"]=="true":
            _sql="SELECT rt.gid, "+table+"."+the_geom+" AS geojson, "+table+".name, mm_length("+table+"."+the_geom+"), "+table+".nature, "+table+".revetement, "+table+".tbllink as tid FROM "+table+", (SELECT edge_id as gid FROM shortest_path('SELECT gid as id,source,target, length as cost from  "+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",false,false)) as rt WHERE "+table+".gid=rt.gid "
#            _sql="SELECT rt.gid, rt.the_geom AS geojson, "+table+".name, length(rt.the_geom) AS length, "+table+".nature, "+table+".revetement, "+table+".tbllink as tid FROM "+table+", (SELECT gid, the_geom FROM dijkstra_sp_delta('"+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",0.01)) as rt WHERE "+table+".gid=rt.gid "
        else:
            if inputs.has_key("priorize") and inputs["priorize"]["value"]=="true":
                _sql="SELECT rt.gid, "+table+"."+the_geom+" AS geojson, "+table+".name, mm_length("+table+"."+the_geom+") AS length, "+table+".nature, "+table+".revetement, "+table+".tbllink as tid FROM "+table+", (SELECT edge_id as gid FROM shortest_path('SELECT gid as id,source,target,CASE WHEN tbllink=0 or tbllink=2 or tbllink=3 THEN length*0.5 ELSE CASE WHEN dp!=''Autre'' and tbllink=1 THEN length*1.75 ELSE length END END as cost from  "+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",false,false)) as rt WHERE "+table+".gid=rt.gid "
            else:
                _sql="SELECT rt.gid, "+table+"."+the_geom+" AS geojson, "+table+".name, mm_length("+table+"."+the_geom+") AS length, "+table+".nature, "+table+".revetement, "+table+".tbllink as tid FROM "+table+", (SELECT edge_id as gid FROM shortest_path('SELECT gid as id,source,target,CASE WHEN tbllink=0 or tbllink=2 or tbllink=3 THEN length*0.65 ELSE CASE WHEN dp!=''Autre'' and tbllink=1 THEN length*2 ELSE length END END as cost from  "+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",false,false)) as rt WHERE "+table+".gid=rt.gid "
    tblName="tmp_route"+str(time.time()).split(".")[0]
    if inputs.keys().count('cnt')>0:
        tblName+=inputs["cnt"]["value"]
    
    #_sql="select sum(gid) as gid, ST_Union(geojson) as geojson,name,nature,revetement,tid from ("+_sql+") as foo GROUP BY foo.tid,foo.name,foo.revetement,foo.nature"
    #print >> sys.stderr,"SQL: "+"SELECT * from get_grouped_road("+_sql+") as foo;"
    
    sql="CREATE TEMPORARY TABLE "+tblName+"1 AS ("+_sql+");"
    sql+="CREATE TEMPORARY TABLE "+tblName+" (id serial, gid int4, geojson text, name text, length float,nature varchar(250),revetement varchar(250),tid int4);"
    sql+="INSERT INTO "+tblName+" (id,gid,geojson,name,length,nature,revetement,tid) (SELECT -1,gid, "+the_geom+" AS geojson, name, mm_length("+the_geom+") AS length, nature, revetement, tbllink as tid from "+table+" WHERE gid="+str(startEdge['gid'])+");"

    sql+="INSERT INTO "+tblName+" (gid,geojson,name,length,nature,revetement,tid) ( SELECT gid,geojson,name,length(geojson),nature,revetement,tid FROM "+tblName+"1);"

    sql+="INSERT INTO "+tblName+" (gid,geojson,name,length,nature,revetement,tid) (SELECT gid, "+the_geom+" AS geojson, name, mm_length("+the_geom+"), nature, revetement, tbllink as tid from "+table+" WHERE gid="+str(endEdge['gid'])+"); "

    sqlUpdateEnd="UPDATE "+tblName+" set geojson=(select CASE WHEN location1=0 OR location1=1 THEN geojson ELSE CASE WHEN location1<location THEN ST_Line_Substring(geojson,location1,location) ELSE ST_Line_Substring(geojson,location,location1) END END  from (SELECT linemerge(geojson) as geojson, ST_line_locate_point(linemerge(geojson), (SELECT ( ST_Intersection(geojson,(SELECT geojson from "+tblName+" ORDER BY id LIMIT 1 OFFSET ((SELECT count(*)-2 from "+tblName+"))))) as location from "+tblName+" ORDER BY id  limit 1 offset (SELECT count(*)-1 from "+tblName+"))) as location,  ST_line_locate_point(linemerge(geojson),ST_line_interpolate_point(linemerge(geojson), ST_line_locate_point(linemerge(geojson), setsrid(geometryFromText('POINT('|| "+ str(inputs["endPoint"]["value"][0]) +" ||' '|| "+ str(inputs["endPoint"]["value"][1]) +" || ')'),4326)))) as location1 from "+tblName+" ORDER BY id limit 1 offset (SELECT count(*)-1 from "+tblName+")) as foo) WHERE gid=(SELECT gid from "+tblName+" ORDER BY id LIMIT 1 OFFSET (SELECT count(*)-1 from "+tblName+"));"

    sqlUpdateFirst=sqlUpdateEnd+"DELETE FROM "+tblName+" WHERE id=(SELECT CASE WHEN (select geojson from "+tblName+" where id=1)=(select geojson from "+tblName+" where id=-1) THEN -1 ELSE NULL END);UPDATE "+tblName+" set geojson=(select CASE WHEN location1=0 OR location1=1 THEN geojson ELSE CASE WHEN location1<location THEN ST_Line_Substring(geojson,location1,location) ELSE ST_Line_Substring(geojson,location,location1) END END  from (SELECT linemerge(geojson) as geojson, ST_line_locate_point(linemerge(geojson), (SELECT ( ST_Intersection(geojson,(SELECT geojson from "+tblName+" ORDER BY id LIMIT 1 OFFSET 1))) as location from "+tblName+" WHERE gid="+str(startEdge['gid'])+")) as location,  ST_line_locate_point(linemerge(geojson),ST_line_interpolate_point(linemerge(geojson), ST_line_locate_point(linemerge(geojson), setsrid(geometryFromText('POINT('|| "+ str(inputs["startPoint"]["value"][0]) +" ||' '|| "+ str(inputs["startPoint"]["value"][1]) +" || ')'),4326)))) as location1 from "+tblName+" WHERE gid="+str(startEdge['gid'])+") as foo) WHERE gid="+str(startEdge['gid'])+";"

    #print >> sys.stderr,"sqlUpdateFirst "+sqlUpdateFirst
    #print >> sys.stderr,"sqlUpdateEnd "+sqlUpdateEnd

    #sqlUpdateFirst=sqlUpdateEnd+"DELETE FROM "+tblName+" WHERE id=(SELECT CASE WHEN (select geojson from "+tblName+" where id=1)=(select geojson from "+tblName+" where id=-1) THEN -1 ELSE NULL END);UPDATE "+tblName+" set geojson=(select CASE WHEN location1=0 OR location1=1 THEN geojson ELSE CASE WHEN location1<location THEN ST_Line_Substring(geojson,location1,location) ELSE ST_Line_Substring(geojson,location,location1) END END  from (SELECT linemerge(geojson) as geojson, ST_line_locate_point(linemerge(geojson), (SELECT ( ST_Intersection(geojson,(SELECT geojson from "+tblName+" where id=2))) as location from "+tblName+" WHERE id=(select min(id) from "+tblName+")) as location,  ST_line_locate_point(linemerge(geojson),ST_line_interpolate_point(linemerge(geojson), ST_line_locate_point(linemerge(geojson), setsrid(geometryFromText('POINT('|| "+ str(inputs["startPoint"]["value"][0]) +" ||' '|| "+ str(inputs["startPoint"]["value"][1]) +" || ')'),4326)))) as location1 from "+tblName+" WHERE id=(select min(id) from "+tblName+")) as foo) WHERE id=(select min(id) from "+tblName+");"

    # Update all other tuples to correct order
    sqlUpdateAll=sqlUpdateEnd+sqlUpdateFirst+"UPDATE "+tblName+" set length=mm_length(geojson) WHERE gid!="+str(startEdge['gid'])+";"


    #print >> sys.stderr,sql
    cur.execute(sql)
    try:
        cur.execute(sqlUpdateAll)
    except:
        try:
            #print >> sys.stderr,"Unable to update all"
            conn.commit();
            cur=conn.cursor()
            cur.execute(sql)
            cur.execute(sqlUpdateFirst)
        except:
            try:
                #print >> sys.stderr,"Unable to update first"
                conn.commit();
                cur=conn.cursor()
                cur.execute(sql)
                cur.execute(sqlUpdateEnd)
            except:
                #print >> sys.stderr,"Unable to update end"
                conn.commit();
                cur=conn.cursor()
                cur.execute(sql)

    # Build the first segment from the starting point to the first edge
    sql1="select 0 as gid, ST_AsGeoJSON(geometryFromText('LINESTRING(' || "+str(inputs["startPoint"]["value"][0])+" || ' ' || "+str(inputs["startPoint"]["value"][1])+" || ', '|| x(ST_Line_Interpolate_Point(linemerge(geojson),location))||' '||y(ST_Line_Interpolate_Point(linemerge(geojson),location))||')'))::text, 'Parcours intermédiaire.'::text, length(geometryFromText('LINESTRING(' || "+str(inputs["startPoint"]["value"][0])+" || ' '|| "+str(inputs["startPoint"]["value"][1])+" || ', '||x(ST_Line_Interpolate_Point(linemerge(geojson),location))||' '||y(ST_Line_Interpolate_Point(linemerge(geojson),location))||')')),'Inconnu','Inconnu',0 from (SELECT *, ST_line_locate_point(linemerge(geojson), setsrid(geometryFromText('POINT('|| "+ str(inputs["startPoint"]["value"][0]) +" ||' '|| "+ str(inputs["startPoint"]["value"][1]) +" || ')'),4326)) as location from "+tblName+" WHERE gid="+str(startEdge['gid'])+") As initialLocation limit 1"
    #print >> sys.stderr,sql1

    # Build the last segment from last edge to the end point
    sql2="select 100000000000 as gid, ST_AsGeoJSON(geometryFromText('LINESTRING( ' || "+str(inputs["endPoint"]["value"][0])+" || ' '|| "+str(inputs["endPoint"]["value"][1])+" || ', '||x(ST_Line_Interpolate_Point(linemerge(geojson),location))||' '||y(ST_Line_Interpolate_Point(linemerge(geojson),location))||')')), 'Parcours intermédiaire.', length(geometryFromText('LINESTRING( ' || "+str(inputs["endPoint"]["value"][0])+" || ' '|| "+str(inputs["endPoint"]["value"][1])+" || ', '||x(ST_Line_Interpolate_Point(linemerge(geojson),location))||' '||y(ST_Line_Interpolate_Point(linemerge(geojson),location))||')')),'Inconnu','Inconnu',100000000000 from (SELECT *, ST_line_locate_point(linemerge(geojson), setsrid(geometryFromText('POINT('|| "+ str(inputs["endPoint"]["value"][0]) +" ||' '|| "+ str(inputs["endPoint"]["value"][1]) +" || ')'),4326)) as location from "+tblName+" WHERE gid="+str(endEdge['gid'])+" ) As finalLocation"
    #print >> sys.stderr,sql2

    # Build the final query as conmbinaison of the previous ones
    #sql+="SELECT * FROM ("+sql1+") as foo0;";
    
    sql="SELECT * FROM (SELECT oldtable.* FROM (select foo.* from (SELECT gid,ST_AsGeoJSON(linemerge(geojson)), name, length(linemerge(GeomFromEWKT(geojson))),nature,revetement,tid FROM (select * from get_grouped_road('"+tblName+"') as (id int4, gid int4,geojson text,name text,length float,nature varchar(250),revetement varchar(250),tid int4)) as foo_1 order by id) as foo) AS oldtable) as foo0";

    #sql="SELECT * FROM (SELECT oldtable.* FROM (select foo.* from (SELECT gid,ST_AsGeoJSON(linemerge(geojson)), name, length(linemerge(geojson)),nature,revetement,tid FROM "+tblName+" order by id) as foo) AS oldtable) as foo0";

    #sql+=""+sql2+";"
    #sql+="SELECT * FROM ("+sql1+") as foo0 UNION (SELECT row_number, oldtable.* FROM (select foo.* from (SELECT gid,ST_AsGeoJSON(linemerge(geojson)), name, length FROM tmp_route"+conf["senv"]["MMID"]+") as foo) AS oldtable CROSS JOIN generate_series(1, (SELECT COUNT(*) FROM tmp_route"+conf["senv"]["MMID"]+")) AS row_number) UNION ("+sql2+")"


    #print >> sys.stderr,sql

    result={"type": "FeatureCollection","features":[]}
    cnt=1

    cur.execute(sql1)
    res1=cur.fetchall()
    #res1=[]

    for i in res1:
        print >> sys.stderr, "I: "+str(i)
        try:
            tmp=unicode(i[2])
        except:
            tmp=i[2]
        result["features"]+=[{"type":"Feature","geometry":json.loads(i[1]),"crs":{"type":"EPSG","properties":{"code":"4326"}}, "properties": {"id":cnt,"name":tmp,"length": i[3]},"nature": i[4],"revetement": i[5],"tid": i[6] }]
        cnt+=1

    cur.execute(sql)
    res=cur.fetchall()

    for i in res:
        try:
            tmp=unicode(i[2])
        except:
            tmp=i[2]
        result["features"]+=[{"type":"Feature","geometry":json.loads(i[1]),"crs":{"type":"EPSG","properties":{"code":"4326"}}, "properties": {"id":cnt,"name":tmp,"length": i[3], "nature": i[4],"revetement": i[5],"tid": i[6]} }]
        cnt+=1

    cur.execute(sql2)
    res2=cur.fetchall()
    #res2=[]

    for i in res2:
        try:
            tmp=unicode(i[2])
        except:
            tmp=i[2]
        result["features"]+=[{"type":"Feature","geometry":json.loads(i[1]),"crs":{"type":"EPSG","properties":{"code":"4326"}}, "properties": {"id":cnt,"name":tmp,"length": i[3], "nature": i[4],"revetement": i[5],"tid": i[6] } }]
        cnt+=1

    conn.close()
    conf["senv"]["last_sid"]=conf["lenv"]["sid"]
    return result

def computeRouteUnion(inputs,cur,startEdge,endEdge,method):
    if method=='SPA' :
        sql="SELECT max(rt.gid), ST_AsGeoJSON(ST_Union(rt.the_geom)) AS geojson, "+table+".name, sum(length(rt.the_geom)) AS length FROM "+table+", (SELECT gid, the_geom FROM astar_sp_delta('"+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",1)) as rt WHERE "+table+".gid=rt.gid ;"
    else:
        if inputs.has_key("distance") and inputs["distance"]["value"]=="true":
            sql="SELECT max(rt.gid), ST_AsGeoJSON(ST_LineMerge(ST_Union("+table+".the_geom))) AS geojson, sum(length(rt.the_geom)) AS length FROM "+table+", (SELECT gid, the_geom FROM dijkstra_sp_delta('"+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",0.01)) as rt WHERE "+table+".gid=rt.gid "
        else:
            sql="SELECT max("+table+".gid), ST_AsGeoJSON(ST_LineMerge(ST_Union("+table+".the_geom))) AS geojson, sum(length("+table+".the_geom)) AS length FROM "+table+", (SELECT edge_id as gid FROM shortest_path('SELECT gid as id,source,target,CASE WHEN tbllink=1 THEN length/2 ELSE length*2 END as cost from  "+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",false,false)) as rt WHERE "+table+".gid=rt.gid "
        sql="SELECT max(rt.gid), ST_AsGeoJSON(ST_LineMerge(ST_Union(rt.the_geom))) AS geojson, sum(length(rt.the_geom)) AS length FROM "+table+", (SELECT gid, the_geom FROM dijkstra_sp_delta('"+table+"',"+str(startEdge['source'])+","+str(endEdge['target'])+",1)) as rt WHERE "+table+".gid=rt.gid ;"
    print >> sys.stderr,sql
        
    cur.execute(sql)
    res=cur.fetchall()
    result={"type": "FeatureCollection","features":[]}
    for i in res:
        try:
            result["features"]+=[{"type":"Feature","geometry":json.loads(i[1]),"crs":{"type":"EPSG","properties":{"code":"4326"}}, "properties": {"id":i[0],"length": i[2]} }]
        except:
            pass
    return result
    
def do(conf,inputs,outputs):
    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    startpointInitial=''.join(inputs["startPoint"]["value"])
    inputs["startPoint"]["value"]=inputs["startPoint"]["value"].split(',')
    if len(inputs["startPoint"]["value"])==2:
        startEdge = findNearestEdge(cur,inputs["startPoint"]["value"])
        inputs["endPoint"]["value"]=inputs["endPoint"]["value"].split(',')
        endEdge = findNearestEdge(cur,inputs["endPoint"]["value"])
        res=computeRoute(cur,startEdge,endEdge,"SPD",conf,inputs)
    else:
        i=0

        endpointInitial="".join(inputs["endPoint"]["value"])

        print >> sys.stderr,endpointInitial+" "+startpointInitial

        startpointInitial=startpointInitial.split(',')

        res={"type": "FeatureCollection","features":[]}
        while i < len(startpointInitial):
            print >> sys.stderr,"Etape "+str(i)
            inputs["startPoint"]["value"]=[startpointInitial[i],startpointInitial[i+1]]
            print >> sys.stderr,str(inputs["startPoint"]["value"])
            startEdge = findNearestEdge(cur,inputs["startPoint"]["value"])
            print >> sys.stderr,str(i+3)+" "+str(len(startpointInitial))
            if i+3<len(startpointInitial):
                inputs["endPoint"]["value"]=[startpointInitial[i+2],startpointInitial[i+3]]
                print >> sys.stderr,str(inputs["endPoint"]["value"])
                endEdge = findNearestEdge(cur,inputs["endPoint"]["value"])
            else:
                print >> sys.stderr,str(inputs["endPoint"]["value"])
                inputs["endPoint"]["value"]=endpointInitial.split(',')
                print >> sys.stderr,str(inputs["endPoint"]["value"])
                endEdge = findNearestEdge(cur,inputs["endPoint"]["value"])
            inputs["cnt"]={"value":str(i)}
            tmp=computeRoute(cur,startEdge,endEdge,"SPD",conf,inputs)
            res["features"]+=tmp["features"];
            i+=2        
    outputs["Result"]["value"]=json.dumps(res)
    conn.close()
    return 3

def doUnion(conf,inputs,outputs):

    conn=psycopg2.connect(parseDb(conf["velodb"]))
    cur=conn.cursor()
    startpointInitial=''.join(inputs["startPoint"]["value"])
    inputs["startPoint"]["value"]=inputs["startPoint"]["value"].split(',')
    if len(inputs["startPoint"]["value"])==2:
        print >> sys.stderr,str(inputs)
        startEdge = findNearestEdge(cur,inputs["startPoint"]["value"])
        print >> sys.stderr,str(inputs)
        inputs["endPoint"]["value"]=inputs["endPoint"]["value"].split(',')
        endEdge = findNearestEdge(cur,inputs["endPoint"]["value"])
        print >> sys.stderr,str(inputs)
        res=computeRouteUnion(inputs,cur,startEdge,endEdge,"SPD")
        outputs["Result"]["value"]=json.dumps(res)
    else:
        i=0

        endpointInitial="".join(inputs["endPoint"]["value"])

        print >> sys.stderr,endpointInitial+" "+startpointInitial

        startpointInitial=startpointInitial.split(',')

        res={"type": "FeatureCollection","features":[]}
        while i < len(startpointInitial):
            print >> sys.stderr,"Etape "+str(i)
            inputs["startPoint"]["value"]=[startpointInitial[i],startpointInitial[i+1]]
            print >> sys.stderr,str(inputs["startPoint"]["value"])
            startEdge = findNearestEdge(cur,inputs["startPoint"]["value"])
            print >> sys.stderr,str(i+3)+" "+str(len(startpointInitial))
            if i+3<len(startpointInitial):
                inputs["endPoint"]["value"]=[startpointInitial[i+2],startpointInitial[i+3]]
                print >> sys.stderr,str(inputs["endPoint"]["value"])
                endEdge = findNearestEdge(cur,inputs["endPoint"]["value"])
            else:
                print >> sys.stderr,str(inputs["endPoint"]["value"])
                inputs["endPoint"]["value"]=endpointInitial.split(',')
                print >> sys.stderr,str(inputs["endPoint"]["value"])
                endEdge = findNearestEdge(cur,inputs["endPoint"]["value"])
            inputs["cnt"]={"value":str(i)}
            tmp=computeRouteUnion(cur,startEdge,endEdge,"SPD")
            print >> sys.stderr,str(tmp)
            if len(res["features"])==0:
                res["features"]+=tmp["features"];
            else:
                res["features"][0]["geometry"]["coordinates"]=tmp["features"][0]["geometry"]["coordinates"]+res["features"][0]["geometry"]["coordinates"];
            i+=2
        outputs["Result"]["value"]=json.dumps(res)

    conn.close()
    return 3

def parseDistance(a):
    if(a/1000>=1):
	tmp=str(a/1000)
	tmp1=tmp.split(".")
	tmp2=a-(eval(tmp1[0])*1000)
	tmp3=str(tmp2).split('.')
	tmp3[0]+""
        if tmp2>=1:
            return " "+str(tmp1[0])+","+str(tmp3[0]+tmp3[1])[0:2]+" km "
        else:
            return " "+str(tmp1[0])
    else:
	tmp=str(a);
	tmp1=tmp.split(".");
	return " "+tmp1[0]+" m ";


def printRoute(conf,inputs,outputs):
    import sys,os
    if list(conf.keys()).count("oo")>0 and list(conf["oo"].keys()).count("external")>0 and conf["oo"]["external"]=="true":
        from subprocess import Popen, PIPE
        import json
        print >> sys.stderr,"Start"
        sys.stderr.flush()
        err_log = file(conf["main"]["tmpPath"]+'/tmp_err_log_file', 'w', 0)
        os.dup2(err_log.fileno(), sys.stderr.fileno())
        process = Popen([conf["oo"]["path"]],stdin=PIPE,stdout=PIPE)
        print >> sys.stderr,"Started"
        script="import  sys\nimport print.PaperMint as PaperMint\n"
        print >> sys.stderr,"PaperMint imported" 
        print >> sys.stderr,script
    else:
        import PaperMint
    sizes={
        "A4l": (1024,768),
        "A4": (768,1024)
        }
    csize=sizes["A4l"]
    
    ext="3"
    if inputs.has_key("components"):
        if inputs["components"]["value"].count("map")==0 or inputs["components"]["value"].count("profile")==0 or inputs["components"]["value"].count("roadmap")==0:
            if inputs["components"]["value"].count("map")>0:
                ext="m"
            if inputs["components"]["value"].count("profile")>0:
                ext+="p"
            if inputs["components"]["value"].count("roadmap")>0:
                ext+="r"
    tmpl="MM-Routing-A4l-template-"+ext+".odt"
    if list(conf.keys()).count("oo")>0 and list(conf["oo"].keys()).count("external")>0 and conf["oo"]["external"]=="true":
        script+="pm=PaperMint.LOClient()\n"
        script+='pm.loadDoc("'+conf["main"]["dataPath"]+'/ftp/templates/'+tmpl+'")\n'
    else:
        pm=PaperMint.LOClient()
        # Load the document
        pm.loadDoc(conf["main"]["dataPath"]+"/ftp/templates/"+tmpl+"")
        
    # Load the map
    import mapscript
    mapfile=conf["main"]["dataPath"]+"/public_maps/project_"+conf["senv"]["last_map"]+".map"
    m=mapscript.mapObj(mapfile)
    for i in range(m.numlayers):
        m.getLayer(i).status=mapscript.MS_OFF
    m.setProjection("init=epsg:900913")

    # Add overlay layers
    mo=mapscript.mapObj(inputs["olayers"]["value"].replace(conf["main"]["mapserverAddress"]+"?map=",""))
    l0=mo.getLayer(0).clone()
    print >> sys.stderr,"+++++++++++++++++++++++++++"
    print >> sys.stderr,m.numlayers
    m.insertLayer(l0)
    m.getLayer(m.numlayers-1).status=mapscript.MS_ON
    print >> sys.stderr,m.numlayers
    print >> sys.stderr,"+++++++++++++++++++++++++++"

    # Set activated layers to on and generate legend icons
    layers=inputs["layers"]["value"].split(",")
    layers+=[mo.getLayer(0).name]
    print >> sys.stderr,layers
    layerNames=[]
    for i in range(0,len(layers)):
        print >> sys.stderr,layers[i]
        layer=m.getLayerByName(layers[i])
        if layer is None:
            i+=1
            layer=m.getLayerByName(layers[i])
        m.getLayer(layer.index).status=mapscript.MS_ON
        prefix=""
        if layer.numclasses==1:
            try:
                layerNames+=["[_"+layer.name+"_] "+layer.metadata.get("ows_title")]
            except:
                layerNames+=["[_"+layer.name+"_] "+layer.name]
        else:
            try:
                toAppend=[m.getLayer(layer.index).get("ows_title")]
            except:
                toAppend=[m.getLayer(layer.index).name]
            for k in range(0,layer.numclasses):
                toAppend+=["[_"+m.getLayer(layer.index).name+"_"+str(k)+"_] "+m.getLayer(layer.index).getClass(k).name]
                
            layerNames+=toAppend

    #We should use a BoundingBoxData here rather than simple string.
    ext=inputs["ext"]["value"].split(',')
    
    #Compute width and width delta
    #width=csize[0]
    #cwidth=float(ext[2])-float(ext[0])
    #wdelta=cwidth/width
    
    #Compute height and height delta
    #height=csize[1]
    #cheight=float(ext[3])-float(ext[1])
    #hdelta=cheight/height

    # Delta
    #delta=float(width)/float(height)
    
    # Fix the maxy value depending on the Delta
    #ext[3]=((1/delta)*(float(ext[2])-float(ext[0])))+float(ext[1])

    # Fix extent based on zoom Level
    if not(inputs.has_key("zoom")):
        import math
        n0=math.log((((20037508.34*2)*csize[0])/(256*(float(ext[2])-float(ext[0])))),2)
        m0=math.log(((20037508.34*csize[1])/(256*(float(ext[3])-float(ext[1])))),2)
        if n0 > m0:
            zl=int(n0)
        else:
            zl=int(m0)
        print >> sys.stderr,"+++++++++++++++++++++++++++++++++++++"
        print >> sys.stderr,zl
        print >> sys.stderr,"+++++++++++++++++++++++++++++++++++++"
    else:
        zl=int(inputs["zoom"]["value"])
	   
    # Strangely on windows / using mapserver 6.0.3 lead to use a different value for 
    # the buffer length around the baselayer (135when 100 was used n standard print)
    delta=(135*(2**(18-zl)))
    m.setExtent(float(ext[0])+delta,float(ext[1])+delta,float(ext[2])-delta,float(ext[3])-delta)

    
    # Fix size
    print >> sys.stderr,"OK"
    m.setSize(csize[0],csize[1])
    print >> sys.stderr,"OK"

    # Replace the Background Map image in the document template if any
    print >> sys.stderr,"OK"
    if inputs.has_key("bgMap"):
        print >> sys.stderr,"OK"
        nl=mapscript.layerObj(m)
        print >> sys.stderr,"OK"
        nl.updateFromString('''LAYER 
 NAME "BaseLayerMap" 
 TYPE RASTER
 UNITS METERS
 STATUS ON
 DATA "'''+inputs["bgMap"]["value"]+'''"
 PROCESSING "RESAMPLE=AVERAGE"
 PROJECTION 
   "init=epsg:900913"
 END
END''')
        print >> sys.stderr,"OK"
        ordon=()
        ordon+=((m.numlayers-1),)
        for a in range(0,m.numlayers-1):
            ordon+=(a,)
        m.setLayerOrder(ordon)
        print >> sys.stderr,"OK"


    if inputs.has_key('profile'):
        import json
        tmp=json.loads(inputs["profile"]["value"])
        distances=json.loads(tmp["features"][0]["properties"]["distance"])
        #print >> sys.stderr,tmp["features"][0]["geometry"]["coordinates"]
        rvals=[[zoo._("Profile")],[],[]]
        totald=0
        for i in range(0,len(distances)):
            rvals[1]+=[parseDistance((totald+distances[i])*111120)]
            totald+=distances[i]
            rvals[2]+=[[tmp["features"][0]["geometry"]["coordinates"][i][2]]]
        if list(conf.keys()).count("oo")>0 and list(conf["oo"].keys()).count("external")>0 and conf["oo"]["external"]=="true":
            script+="pm.statThis(\"[_profile_]\","+json.dumps(rvals)+")\n"



    if inputs.has_key('route'):
        import vector_tools.service as vt
        import osgeo.ogr as ogr
        geoms=vt.readFileFromBuffer(inputs["route"]["value"],"xml")
        rvals0=[[zoo._("Step"),zoo._("Path"),zoo._("Distance"),zoo._("Type")]]
        for ij in range(0,len(geoms)):
            rvals0+=[[geoms[ij].GetField(2),geoms[ij].GetField(3),parseDistance(geoms[ij].GetField(1)*111120),"[_route_danger_]"]]

    # Draw the image and save it
    print >> sys.stderr,"Draw"
    i=m.draw()
    print >> sys.stderr,"OK"
    import time
    savedImage=conf["main"]["tmpPath"]+"/print_"+conf["senv"]["MMID"]+"_"+str(time.clock()).split(".")[1]+".png"
    print >> sys.stderr,"OK"
    try:
        os.unlink(savedImage)
    except:
        pass
    print >> sys.stderr,"OK"
    i.save(savedImage)
    print >> sys.stderr,"OK"

    # Set activated layers to on
    #layers=inputs["layers"]["value"].split(",")
    script0=""
    for i in range(0,len(layers)):
        print >> sys.stderr,layers[i]
        layer=m.getLayerByName(layers[i])
        if layer is None:
            i+=1
            layer=m.getLayerByName(layers[i])
        if layer.name!="Result":
            lm=mapscript.mapObj(conf["main"]["dataPath"]+"/public_maps/map4legend_"+conf["senv"]["last_map"]+"_"+layer.name+".map")
        else:
            lm=mapscript.mapObj(conf["main"]["dataPath"]+"/maps/map4legend_StyleRoute_network2.map")
        lm.setSize(20,20)
        lm.setExtent(-1.5,-1.5,7.5,7.5)
        if layer.numclasses==1:
            lm.getLayer(0).status=mapscript.MS_ON
            lsavedImage=conf["main"]["tmpPath"]+"/print_"+conf["senv"]["MMID"]+"_"+str(time.clock()).split(".")[1]+".png"
            print >> sys.stderr,"OK"
            try:
                os.unlink(lsavedImage)
            except:
                pass
            img=lm.draw()
            img.save(lsavedImage)
            script0+='pm.insertImageAt("[_'+layer.name+'_]","'+lsavedImage+'",True)\n'
        else:
            for k in range(0,layer.numclasses):
                if layer.name!="Result":
                    lm=mapscript.mapObj(conf["main"]["dataPath"]+"/maps/map4legend_"+conf["senv"]["last_map"]+"_"+layer.name+".map")
                else:
                    lm=mapscript.mapObj(conf["main"]["dataPath"]+"/maps/map4legend_StyleRoute_network2.map")
                lm.setSize(20,20)
                lm.setExtent(-1.5,-1.5,7.5,7.5)
                lm.getLayer(k).status=mapscript.MS_ON
                for j in range(0,k-1):
                    lm.getLayer(j).status=mapscript.MS_OFF
                for j in range(k+1,lm.numlayers):
                    lm.getLayer(j).status=mapscript.MS_OFF
                lsavedImage=conf["main"]["tmpPath"]+"/print_"+conf["senv"]["MMID"]+"_"+str(time.clock()).split(".")[1]+".png"
                print >> sys.stderr,"OK"
                try:
                    os.unlink(lsavedImage)
                except:
                    pass
                img=lm.draw()
                img.save(lsavedImage)
                if  layer.name!="Result":
                    script0+='pm.insertImageAt("[_'+layer.name+"_"+str(k)+'_]","'+lsavedImage+'",True)\n'
                else:
                    script0+='pm.insertImageAt("[_Result_'+str(k)+'_]","'+lsavedImage+'",True)\n'
        if layer.name=="Result":
            break


    if list(conf.keys()).count("oo")>0 and list(conf["oo"].keys()).count("external")>0 and conf["oo"]["external"]=="true":
        script+='pm.searchAndReplaceImage("Map","'+savedImage+'")\n'
        script+='pm.searchAndReplace("[_map_title_]","'+m.web.metadata.get("mmTitle")+'")\n'
        script+='pm.addList("[_Legend_]",'+json.dumps(layerNames)+' )\n'
        script+=script0
    else:
        # Replace the Map image in the document template
        pm.searchAndReplaceImage("Map",savedImage)
    
        # Replace the map_title field with Project Name
        pm.searchAndReplace("[_map_title_]",m.web.metadata.get("mmTitle"))

        # Replace the Legend field with Project Name
        pm.addList("[_Legend_]",layerNames)



    if inputs.has_key('route'):
        if list(conf.keys()).count("oo")>0 and list(conf["oo"].keys()).count("external")>0 and conf["oo"]["external"]=="true":
            script+="pm.addTable(\"[_steps_]\","+json.dumps(rvals0)+")\n"
            script+="pm.insertImageAt('[_route_danger_]','C:/inetpub/wwwroot/public_map/img/design/amenagements/route_danger.png')\n"


    # Save the document
    docPath=conf["main"]["tmpPath"]+"/"+conf["senv"]["MMID"]+"_"+str(time.clock()).split(".")[1]+"_"+inputs["tDoc"]["value"]
    if list(conf.keys()).count("oo")>0 and list(conf["oo"].keys()).count("external")>0 and conf["oo"]["external"]=="true":
        script+='print("'+docPath+'",file=sys.stderr)\n'
        script+='pm.saveDoc("'+docPath+'")\n'
        script+='pm.unloadDoc("'+conf["main"]["dataPath"]+'/ftp/templates/'+tmpl+'")\n'
        try:
            print >> sys.stderr,"Run0"
            print >> sys.stderr,script
            process.stdin.write(script)
            print >> sys.stderr,"Run1"
            process.stdin.close()
            print >> sys.stderr,"Run2"
            process.wait()
            conf["lenv"]["message"]=str(process.stdout.readline())
            sys.stderr.flush()
            sys.stderr.close()
            err_log=file(conf["main"]["tmpPath"]+'/tmp_err_log_file', 'r', 0)
            conf["lenv"]["message"]+=str(err_log.read())
        except Exception,e:
            conf["lenv"]["message"]="Unable to print your document :"+str(e)
            return zoo.SERVICE_FAILED
    else:
        pm.saveDoc(docPath)
        pm.unloadDoc(conf["main"]["dataPath"]+"/ftp/templates/"+tmpl+"")
    
    try:
        outputs["Result"]["value"]=open(docPath,"rb").read()
    except Exception,e:
        conf["lenv"]["message"]+=str(e)
        return zoo.SERVICE_FAILED

    # unlink Failed on WIN32 because the SOffice server is running by another
    # user than the IIS AppPool\DefaultAppPool responsible for accessing files
    # from services
    try:
        os.unlink(docPath)
    except:
        pass
    return zoo.SERVICE_SUCCEEDED
