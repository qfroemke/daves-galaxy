#!/usr/bin/python2

from newdominion.dominion.models import *
from newdominion.dominion.util import *
from django.db import connection, transaction
from django.db.models import Avg, Max, Min, Count
import sys
import os
import random
import time
import newdominion.settings
import copy
from pprint import pprint

def doencounter(f1, f2, f1report, f2report):
  f1 = Fleet.objects.get(id=f1.id)
  f2 = Fleet.objects.get(id=f2.id)
  if f1.numships() == 0:
    return
  if f2.numships() == 0:
    return
  p1 = f1.owner.get_profile()
  p2 = f2.owner.get_profile()
  relation = p1.getpoliticalrelation(p2)
  if f2 == f1 or relation == "friend":
    #print "friendly encounter"
    return
  if f1.disposition == 9:
    #print "piracy..."
    dopiracy(f1,f2, f1report, f2report)
  elif f2.disposition == 9:
    #print "piracy..."
    dopiracy(f2,f1, f2report, f1report)
  elif relation == "enemy":
    #print "battle..."
    dobattle(f1,f2, f1report,f2report)
  else:
    return

def dopiracy(f1, f2, f1report, f2report):
  if f1.numships() == 0:
    return
  if f2.numships() == 0:
    return
  distance = getdistance(f1.x,f1.y,f2.x,f2.y)
  relations = f1.owner.get_profile().getpoliticalrelation(f2.owner.get_profile())
  # see who is pirating who...

  replinestart1 = "Piracy - Fleet # " + str(f1.id) + "(pirate) "
  replinestart2 = "Piracy - Fleet # " + str(f2.id) + "(pirate's target) "
  if f2.numcombatants() > 0: 
    # Ok, f2 has combatants, so attempt to sulk away,
    # unless f2 is wise to f1's piratical nature
    # (f2 attacks f1 if within sense range and
    # a random factor is met...
    f1report.append(replinestart1 + "The other fleet is not a pushover...")
    if distance < f2.senserange():
      if relations == "enemy":
        f1report.append(replinestart1 + "They see us and are attacking.")
        f2report.append(replinestart2 + "Pirate scum found.")
        dobattle(f2,f1, f2report, f1report)
      elif random.random() < .25:
        f1report.append(replinestart1 + "Found by neutral combatants.  ")
        f2report.append(replinestart2 + "Neutral pirate scum found, attacking.")
        dobattle(f2,f1, f2report, f1report)
  else:
    # aha, actual piracy happens here --
    outcome = random.random()
    if outcome < .7:          # cargo got dropped
      f1report.append(replinestart1 + "Prey dropped cargo, retrieved.")
      f2report.append(replinestart2 + "Pirates attacked, we dropped our cargo to escape.")
      if f2.trade_manifest:
        if f1.trade_manifest is None:
          f1.trade_manifest = Manifest()
        for item in f2.trade_manifest.manifestlist(['id','people','quatloos']):
          setattr(f1,item,getattr(f1.trade_manifest,item)+getattr(f2.trade_manifest,item))
          setattr(f2,item,0)
        f2.damaged = True
        f2.gotoplanet(f2.homeport)
      else:
        f1report.append(replinestart1 + "Prey escaped.")
        f2report.append(replinestart2 + "Pirates seen.")
        # there's nothing to steal, odd...
    elif outcome < .9:        # duke it out...
      dobattle(f1,f2,f1report,f2report)
    else:                     # surrender...
      f1report.append(replinestart1 + "Prey surrendered.")
      f2report.append(replinestart2 + "Surrendered to Pirates.")
      for shiptype in f2.shiptypeslist():
        setattr(f1,shiptype.name,getattr(f1,shiptype.name)+getattr(f2,shiptype.name))
        setattr(f2,shiptype.name,0)
      if f2.trade_manifest is not None:
        if f1.trade_manifest is None:
          f1.trade_manifest = Manifest()
        for item in f2.trade_manifest.manifestlist(['id']):
          setattr(f1,item,getattr(f1.trade_manifest,item)+getattr(f2.trade_manifest,item))
          setattr(f2,item,0)
        f1.trade_manifest.save()
      f1.save()
      # delete later...
      f2.save()



def doattack(fleet1, fleet2, minatt=0, justonce=True):
  dead = []
  done = 1

  # if one fleet is much bigger than the other,
  # assume that  
  startship = 0
  multiplier = 1.2 
  if len(fleet1) > len(fleet2)*multiplier:
    startship = len(fleet1)-int(max(0,((len(fleet2)*multiplier))))

  for i in xrange(startship,len(fleet1)):
    while fleet1[i]['att'] >= minatt:
      done = 0 
      if random.random() < .3:
        # see if we've hit something...
        hit = random.randint(0,len(fleet2)-1)
        dodged = False
        # you get 3 chances to dodge (if you have defences left...)
        for j in xrange(4):
          if fleet2[hit]['def'] and random.random() < .6:
            fleet2[hit]['def'] -= 1
            # successful defense
            dodged = True
            break
        if not dodged:
          # kaboom...
          dead.append(hit)
      fleet1[i]['att'] -= 1
      if justonce == True:
        break

  return done, dead


def testtotalcost(fleettype, planet):
  cost = 0
  for c in shiptypes[fleettype]['required']:
    amount = shiptypes[fleettype]['required'][c]
    if c == 'quatloos':
      cost += amount
    else:
      cost += amount * planet.getprice(c,False,{})
  return cost

  


def testcombat(f1, f2):
  avgs = {}
  random.seed(0)
  
  for j in f1.shiplist():
    avgs['f1'+j]=0.0
  for j in f2.shiplist():
    avgs['f2'+j]=0.0
  for i in xrange(50):
    f1t = copy.copy(f1)
    f2t = copy.copy(f2)
    dobattle(f1t,f2t,[],[])
    for j in f1.shiplist():
      total = avgs['f1'+j]
      new = getattr(f1t,j)
      avgs['f1'+j] = total+new
    for j in f2.shiplist():
      total = avgs['f2'+j]
      new = getattr(f2t,j)
      avgs['f2'+j] = total+new
  for j in f1.shiplist():
    print "f1: ",
    total = avgs['f1'+j]
    avg = total/50
    setattr(f1,j,int(avg))
    print j + ": " + str(avg),
  print " --"
  for j in f2.shiplist():
    print "f2: ",
    total = avgs['f2'+j]
    avg = total/50
    setattr(f2,j,int(avg))
    print j + ": " + str(avg),
  print " --"

def testcosteffectiveness(type1, type2, f1, f2, planet):
  acost = float(testtotalcost(type1,planet))
  bcost = float(testtotalcost(type2,planet))
  numa = 1000
  numb = int((acost/bcost)*1000)
  setattr(f1, type1, numa) 
  setattr(f2, type2, numb)
  print type1 + " --> " + str(getattr(f1,type1))
  print type2 + " --> " + str(getattr(f2,type2))
  testcombat(f1,f2)
  
  print type1 + " - %.2f"%(float(getattr(f1,type1))/numa)+"%"
  print type2 + " - %.2f"%(float(getattr(f2,type2))/numb)+"%"
  setattr(f1, type1, 0) 
  setattr(f2, type2, 0)

def dobattle(f1, f2, f1report, f2report):
  """
  >>> random.seed(0)
  >>> s = Sector(key=125123,x=100,y=100)
  >>> s.save()
  >>> u = User(username="dobattle")
  >>> u.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p = Planet(resources=r, society=75,owner=u, sector=s,
  ...            x=626, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p.save()
  >>> pl = Player(user=u, capital=p, color=112233)
  >>> pl.lastactivity = datetime.datetime.now()
  >>> pl.save()

  >>> u2 = User(username="dobattle2")
  >>> u2.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p2 = Planet(resources=r, society=75,owner=u2, sector=s,
  ...            x=626, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p2.save()
  >>> pl2 = Player(user=u2, capital=p2, color=112233)
  >>> pl2.lastactivity = datetime.datetime.now()
  >>> pl2.save()
  >>> pl2.setpoliticalrelation(pl,'enemy')
  >>> f1 = Fleet(owner=u, sector=s, x=626.5, y=617.5)
  >>> f1.save()
  >>> f2 = Fleet(owner=u2, sector=s, x=626.5, y=617.5)
  >>> f2.save()
  >>> for i in shiptypes:
  ...   stype = shiptypes[i]
  ...   if stype['att'] > 0:
  ...     spread = 0
  ...     avg = 0
  ...     print "--- " + i
  ...     for j in xrange(50):
  ...       setattr(f1,i,50)
  ...       setattr(f2,i,50)
  ...       dobattle(f1,f2,[],[])
  ...       spread += abs(getattr(f1,i)-getattr(f2,i))
  ...       avg += getattr(f1,i)
  ...       avg += getattr(f2,i)
  ...       #print "(" + str(getattr(f1,i)) + "," + str(getattr(f2,i)) + ") ",
  ...     spread /= 50.0
  ...     avg /= 100.0
  ...     print "s="  + str(spread)
  ...     print "a="  + str(avg)
  ...     setattr(f1,i,0)
  ...     setattr(f2,i,0)
  --- subspacers
  s=7.4
  a=24.0
  --- cruisers
  s=8.54
  a=24.93
  --- fighters
  s=7.8
  a=23.22
  --- frigates
  s=5.8
  a=32.0
  --- superbattleships
  s=4.06
  a=39.65
  --- destroyers
  s=6.86
  a=30.65
  --- scouts
  s=5.84
  a=27.04
  --- battleships
  s=5.36
  a=38.7

  >>> f1.battleships = 0 
  >>> f1.destroyers = 20
  >>> f1.frigates = 0
  >>> f2.frigates = 20 
  >>> testcombat(f1,f2)
  f1:  destroyers: 18.38  --
  f2:  frigates: 5.84  --

  >>> f1.destroyers = 20
  >>> f1.frigates = 0
  >>> f2.frigates = 0
  >>> f2.cruisers = 20
  >>> testcombat(f1,f2)
  f1:  destroyers: 5.44  --
  f2:  cruisers: 18.02  --

  >>> f1.cruisers = 0
  >>> f1.destroyers = 0
  >>> f1.battleships = 20
  >>> testcombat(f1,f2)
  f1:  battleships: 19.16  --
  f2:  cruisers: 2.26  --
 
  >>> f1.cruisers = 0
  >>> f2.cruisers = 0
  >>> f2.superbattleships = 20
  >>> testcombat(f1,f2)
  f1:  battleships: 8.32  --
  f2:  superbattleships: 17.68  --
 
  >>> f1.superbattleships=0
  >>> f2.superbattleships=0
  >>> f1.battleships = 0

  >>> testcosteffectiveness('subspacers','frigates',f1,f2,p)
  subspacers --> 1000
  frigates --> 1353
  f1:  subspacers: 524.68  --
  f2:  frigates: 1003.3  --
  subspacers - 0.52%
  frigates - 0.74%
 
  >>> testcosteffectiveness('frigates','destroyers',f1,f2,p)
  frigates --> 1000
  destroyers --> 728
  f1:  frigates: 593.92  --
  f2:  destroyers: 455.32  --
  frigates - 0.59%
  destroyers - 0.62%

  >>> testcosteffectiveness('frigates','cruisers',f1,f2,p)
  frigates --> 1000
  cruisers --> 395
  f1:  frigates: 694.9  --
  f2:  cruisers: 302.38  --
  frigates - 0.69%
  cruisers - 0.76%

  >>> testcosteffectiveness('frigates','battleships',f1,f2,p)
  frigates --> 1000
  battleships --> 194
  f1:  frigates: 848.46  --
  f2:  battleships: 180.48  --
  frigates - 0.85%
  battleships - 0.93%

  >>> testcosteffectiveness('frigates','superbattleships',f1,f2,p)
  frigates --> 1000
  superbattleships --> 99
  f1:  frigates: 930.58  --
  f2:  superbattleships: 92.92  --
  frigates - 0.93%
  superbattleships - 0.93%

  >>> testcosteffectiveness('destroyers','cruisers',f1,f2,p)
  destroyers --> 1000
  cruisers --> 543
  f1:  destroyers: 756.12  --
  f2:  cruisers: 325.98  --
  destroyers - 0.76%
  cruisers - 0.60%


  >>> testcosteffectiveness('destroyers','battleships',f1,f2,p)
  destroyers --> 1000
  battleships --> 266
  f1:  destroyers: 878.7  --
  f2:  battleships: 239.12  --
  destroyers - 0.88%
  battleships - 0.90%

  >>> testcosteffectiveness('destroyers','superbattleships',f1,f2,p)
  destroyers --> 1000
  superbattleships --> 136
  f1:  destroyers: 947.84  --
  f2:  superbattleships: 123.86  --
  destroyers - 0.95%
  superbattleships - 0.90%

  >>> testcosteffectiveness('cruisers','battleships',f1,f2,p)
  cruisers --> 1000
  battleships --> 491
  f1:  cruisers: 748.3  --
  f2:  battleships: 388.58  --
  cruisers - 0.75%
  battleships - 0.79%

  >>> testcosteffectiveness('cruisers','superbattleships',f1,f2,p)
  cruisers --> 1000
  superbattleships --> 250
  f1:  cruisers: 901.04  --
  f2:  superbattleships: 216.74  --
  cruisers - 0.90%
  superbattleships - 0.86%

  >>> pprint(p.getprices([]))
  {'antimatter': 4862,
   'consumergoods': 29,
   'food': 9,
   'hydrocarbon': 100,
   'krellmetal': 9724,
   'people': 88,
   'steel': 97,
   'unobtanium': 19449}
  """

  def generatelossreport(casualties1,casualties2,f1report,
                         f1replinestart,f2replinestart):
    if len(casualties1):
      f1report.append(f1replinestart + "Our Ships Lost:")
      for casualties in casualties1:
        f1report.append("   %20s -- %d" % (casualties, casualties1[casualties]))

    if len(casualties2):
      f1report.append(f2replinestart + "Their Ships Lost:")
      for casualties in casualties2:
        f1report.append("   %20s -- %d" % (casualties, casualties2[casualties]))
  
  def removedestroyed(dead,casualtylist,fleet):
    # remove duplicates and sort last to first
    dead = sorted(list(set(dead)),reverse=True)
    for i in dead:
      #print str(i) + " - " + str(len(fleet))
      if not casualtylist.has_key(fleet[i]['type']):
        casualtylist[fleet[i]['type']] = 1
      else: 
        casualtylist[fleet[i]['type']] += 1

      fleet.pop(i)

  report = []
  total1 = f1.numships()
  total2 = f2.numships()
  noncombatants1 = f1.numnoncombatants() 
  noncombatants2 = f2.numnoncombatants() 
  combatants1 = f1.numcombatants() 
  combatants2 = f2.numcombatants() 
  casualties1 = {}
  casualties2 = {}
 
  if total1 == 0:
    return
  if total2 == 0:
    return
  
  f1replinestart = "Fleet: " + f1.shortdescription(html=0) + " (" + str(f1.id) + ") Battle! -- "
  f2replinestart = "Fleet: " + f2.shortdescription(html=0) + " (" + str(f2.id) + ") Battle! -- "
  

  # what if we had a war, and nobody could fight?
  if combatants1 == 0 and combatants2 == 0:
    f1report.append(f1replinestart + "Menacing jestures were made, but no damage was done.")
    f2report.append(f2replinestart + "Menacing jestures were made, but no damage was done.")
    return

  fleet1 = f1.listrepr()
  fleet2 = f2.listrepr()
  
  distance = getdistance(f1.x,f1.y,f2.x,f2.y)

  attackoccurred = 0

  done1 = 0
  done2 = 0 
  
  counter = 1 
  
  dead1=[]
  dead2=[]
  
  done1, dead2 = doattack(fleet1, fleet2,0,True)
  done2, dead1 = doattack(fleet2, fleet1,0,True) 
  
  while (not (done1 and done2)) and len(fleet1) and len(fleet2):
    if fleet1[0]['att'] > fleet2[0]['att'] and counter % 4 != 1:
      done1, dead2 = doattack(fleet1, fleet2,fleet2[0]['att'])
    elif fleet2[0]['att'] > fleet1[0]['att'] and counter % 4 != 1:
      done2, dead1 = doattack(fleet2, fleet1,fleet2[0]['att']) 
    else:
      done1, dead2 = doattack(fleet1, fleet2)
      done2, dead1 = doattack(fleet2, fleet1) 

    if len(dead1) > 0:
      removedestroyed(dead1,casualties1,fleet1)
      dead1 = []

    if len(dead2) > 0:
      removedestroyed(dead2,casualties2,fleet2)
      dead2 = []
    
    counter += 1

          #fleet2.pop(hit)
    
  if len(casualties1) or len(casualties2):
    # write a report...
    generatelossreport(casualties1,casualties2,
                       f1report,f1replinestart,f2replinestart)
    generatelossreport(casualties2,casualties1,
                       f2report,f2replinestart,f1replinestart)


  if total1 > len(fleet1):
    f1.damaged = True
  if total2 > len(fleet2):
    f2.damaged = True

  for type in shiptypes:
    setattr(f1, type, 0)
    setattr(f2, type, 0)

  if len(fleet1):
    for ship in fleet1:
      setattr(f1, ship['type'], getattr(f1,ship['type']) + 1)
  else:
    f1.destroyed = True

  if len(fleet2):
    for ship in fleet2:
      setattr(f2, ship['type'], getattr(f2,ship['type']) + 1)
  else:
    f2.destroyed = True

  f1.save()
  f2.save()




@print_timing
def dobuildinview2():
  """
  >>> u = User(username="dobuildinview2")
  >>> u.save()
  >>> u2 = User(username="dobuildinview2-2")
  >>> u2.save()
  >>> r = Manifest(people=5000, food=1000)
  >>> r.save()
  >>> x1 = 500.1
  >>> y1 = 500.1
  >>> s = Sector(key=buildsectorkey(x1,y1),x=101,y=101)
  >>> s.save()

  >>> s1 = Sector(key=buildsectorkey(x1-5,y1-5),x=100,y=100)
  >>> s1.save()
  >>> s2 = Sector(key=buildsectorkey(x1-5,y1),x=100,y=100)
  >>> s2.save()
  >>> s3 = Sector(key=buildsectorkey(x1-5,y1+5),x=100,y=100)
  >>> s3.save()

  >>> s4 = Sector(key=buildsectorkey(x1,y1-5),x=100,y=100)
  >>> s4.save()
  >>> s5 = Sector(key=buildsectorkey(x1,y1+5),x=100,y=100)
  >>> s5.save()

  >>> s6 = Sector(key=buildsectorkey(x1+5,y1-5),x=100,y=100)
  >>> s6.save()
  >>> s7 = Sector(key=buildsectorkey(x1+5,y1),x=100,y=100)
  >>> s7.save()
  >>> s8 = Sector(key=buildsectorkey(x1+5,y1+5),x=100,y=100)
  >>> s8.save()
  >>> p = Planet(resources=r, society=1,owner=u, sector=s,
  ...            x=505.5, y=506.5, r=.1, color=0x1234)
  >>> p.save()
  >>> p2 = Planet(resources=r, sensorrange=1, society=1,owner=u2, sector=s,
  ...            x=505.5, y=509.5, r=.1, color=0x1234)
  >>> p2.save()
  >>> f = Fleet(owner=u, homeport=p, destroyers=1, sensorrange=1, sector=s, x=p.x,y=p.y)
  >>> f.save()
  >>> f1 = Fleet(owner=u2, homeport=p, scouts=1, sector=s, x=p.x+.1,y=p.y)
  >>> f1.save()
  >>> f2 = Fleet(owner=u2, homeport=p, scouts=1, sector=s, x=p.x,y=p.y+.1)
  >>> f2.save()
  >>> f3 = Fleet(owner=u2, homeport=p, scouts=1, sector=s, x=p.x+.1,y=p.y+.1)
  >>> f3.save()
  >>> # senserange is 0:
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f = Fleet.objects.get(destroyers=1)
  >>> f.inviewoffleet.count()
  0
  >>> # senserange is 1:
  >>> f1.sensorrange=1
  >>> f1.save()
  >>> f2.sensorrange=1
  >>> f2.save()
  >>> f3.sensorrange=1
  >>> f3.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f = Fleet.objects.get(destroyers=1)
  >>> f.inviewoffleet.count()
  3
  >>> f.x = 500.1
  >>> f.y = 500.1
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> f1.x = 499.9
  >>> f1.y = 499.9
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 499.9
  >>> f2.y = 500.1
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 500.1
  >>> f3.y = 499.9
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  >>> f.inviewoffleet.count()
  0
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.x = 504.9
  >>> f.y = 500.1
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  0
  >>> f1.x = 504.9
  >>> f1.y = 499.9
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 505.1
  >>> f2.y = 499.9
  >>> print str(buildsectorkey(f2.x, f2.y))
  101099
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 505.1
  >>> f3.y = 500.1
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.x = 504.9
  >>> f.y = 504.9
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  0
  >>> f1.x = 505.1
  >>> f1.y = 504.9
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 505.1
  >>> f2.y = 505.1
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 504.9
  >>> f3.y = 505.1
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.x = 500.1
  >>> f.y = 504.9
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  0
  >>> f1.x = 500.1
  >>> f1.y = 505.1
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 499.9
  >>> f2.y = 505.1
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 499.9
  >>> f3.y = 504.9
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.owner.inviewof.count()
  4
  >>> # now test planet --> fleet
  >>> f1.x = 0
  >>> f1.save()
  >>> f2.x = 0
  >>> f2.save()
  >>> f3.x = 0
  >>> f3.save()
  >>> f.x = p2.x
  >>> f.y = p2.y+.1
  >>> f.save()
  >>> doclearinview()
  >>> dobuildinview2()
  >>> p2.owner.inviewof.count()
  4
  >>> p.owner.inviewof.count()
  1
  >>> # test sneakiness
  >>> f.subspacers = 1
  >>> f.destroyers = 0
  >>> f.y = p2.y+.5
  >>> f.save()
  >>> random.seed(1)
  >>> doclearinview()
  >>> dobuildinview2()
  >>> p2.owner.inviewof.count()
  3
  >>> random.seed(2)
  >>> doclearinview()
  >>> dobuildinview2()
  >>> p2.owner.inviewof.count()
  4
  """
  def cansee(viewer,fleet):
    d = getdistance(viewer['x'],viewer['y'],fleet['x'],fleet['y'])
    if d < viewer['sensorrange']:
      if issneaky(fleet):
        if random.random() > (d/viewer['sensorrange'])*1.2:
          return True
        else:
          return False
      else:
        return True




  def issneaky(fleet):
    if fleet['subspacers'] == 0:
      return False
    for shiptype in shiptypes.keys():
      if fleet[shiptype] > 0 and shiptype != 'subspacers':
        return False
    # must be sneaky
    return True
  
  
  def scansectorfleets(f1, sector, scanrange):
    for i in scanrange:
      f2 = sector[i]
      if f1['owner_id'] != f2['owner_id']:
        if cansee(f1,f2):
          addtodefinite(fleetfleetview, [(str(f2['id']),str(f1['id']))])
          addtodefinite(fleetplayerview, [(str(f2['id']),str(f1['owner_id']))])
          for j in users[f1['owner_id']].friendly:
            addtodefinite(fleetplayerview, [(str(f2['id']),str(j))])
            
        if cansee(f2,f1):
          addtodefinite(fleetfleetview, [(str(f1['id']),str(f2['id']))])
          addtodefinite(fleetplayerview, [(str(f1['id']),str(f2['owner_id']))])
          for j in users[f2['owner_id']].friendly:
            addtodefinite(fleetplayerview, [(str(f1['id']),str(j))])

  def scansectorplanets(f, sector):
    for i in xrange(len(sector)):
      p = sector[i]
      if f['owner_id'] != p['owner_id']:
        if cansee(p,f):
          addtodefinite(fleetplayerview, [(str(f['id']),str(p['owner_id']))])
          for j in users[p['owner_id']].friendly:
            addtodefinite(fleetplayerview, [(str(f['id']),str(j))])

  def addtodefinite(deflist, stuff):
    for i in stuff:
      if not deflist.has_key(i):
        deflist[i] = 1
    
  userlist = User.objects.all()
  users = {}
  for u in userlist:
    if u.player_set.count() > 0:
      u.friendly = u.get_profile().friends.all().values_list('user_id',flat=True)
    else:
      u.friendly = []
    users[u.id] = u 

  fleets = Fleet.objects.all().values()
 
  fleetsbysector = {}
  fleetsbyowner = {}

  planetsbysector = {}
  planetsbyowner = {}

  for f in fleets.iterator():
    if f['sector_id'] not in fleetsbysector:
      fleetsbysector[f['sector_id']] = []
    fleetsbysector[f['sector_id']].append(f)

    if f['owner_id'] not in fleetsbyowner:
      fleetsbyowner[f['owner_id']] = []
    fleetsbyowner[f['owner_id']].append(f)

  planets = Planet.objects.exclude(owner=None).values('id','sector_id',
                                                      'owner_id','sensorrange',
                                                      'x','y')

  for p in planets:
    if p['sector_id'] not in planetsbysector:
      planetsbysector[p['sector_id']] = []
    planetsbysector[p['sector_id']].append(p)

    if p['owner_id'] not in planetsbyowner:
      planetsbyowner[p['owner_id']] = [] 
    planetsbyowner[p['owner_id']].append(p)


  
 
  fleetplayerview = {}
  fleetfleetview = {}

  for sid in fleetsbysector:
    s = fleetsbysector[sid]
    startx = int(s[0]['x'])/5*5
    starty = int(s[0]['y'])/5*5
    endx = startx+5
    endy = starty+5

    for i in xrange(len(s)):
      f1 = s[i]
      #print "---"
      #print str(f1['x']) + "," + str(f1['y'])
      addtodefinite(fleetplayerview, [(str(f1['id']),str(f1['owner_id']))])
      for j in users[f1['owner_id']].friendly:
        addtodefinite(fleetplayerview, [(str(f1['id']),str(j))])
      
      scansectorfleets(f1, s, xrange(i+1,len(s)))
      if planetsbysector.has_key(sid):
        scansectorplanets(f1, planetsbysector[sid])

      othersectors = [] 
      
      #check adjoining sectors if needed
      if f1['x']-f1['sensorrange'] < startx:
        #print "-."
        othersectors.append(buildsectorkey(startx-1,starty))
        if f1['y']-f1['sensorrange'] < starty:
          #print "--" + str(buildsectorkey(startx-1,starty-1))
          othersectors.append(buildsectorkey(startx-1,starty-1))
        elif f1['y']+f1['sensorrange'] > endy:
          #print "-+"
          othersectors.append(buildsectorkey(startx-1,endy+1))

      elif f1['x']+f1['sensorrange'] > endx:
        #print "+."
        othersectors.append(buildsectorkey(endx+1,starty))
        if f1['y']-f1['sensorrange'] < starty:
          #print "+-"
          othersectors.append(buildsectorkey(endx+1,starty-1))
        elif f1['y']+f1['sensorrange'] > endy:
          #print "+-"
          othersectors.append(buildsectorkey(endx+1,endy+1))
      
      if f1['y']-f1['sensorrange'] < starty:
        #print ".-"
        othersectors.append(buildsectorkey(startx,starty-1))

      elif f1['y']+f1['sensorrange'] > endy:
        #print ".+"
        othersectors.append(buildsectorkey(startx,endy+1))
      
      for osid in othersectors:
        if fleetsbysector.has_key(osid):
          os = fleetsbysector[osid]
          scansectorfleets(f1, os, xrange(len(os)))
        if planetsbysector.has_key(osid):
          os = planetsbysector[osid]
          scansectorplanets(f1, os)

  insertrows('dominion_fleet_inviewof',
             ('fleet_id', 'user_id'),
             fleetplayerview.keys())
  insertrows('dominion_fleet_inviewoffleet',
             ('from_fleet_id', 'to_fleet_id'),
             fleetfleetview.keys())




@print_timing
def doclearinview():
  cursor = connection.cursor()

  # Data modifying operation
  cursor.execute("DELETE FROM dominion_fleet_inviewof;")
  cursor.execute("DELETE FROM dominion_fleet_inviewoffleet;")
  #cursor.execute("DELETE FROM dominion_player_neighbors;")

  # Since we modified data, mark the transaction as dirty
  transaction.set_dirty()



@transaction.commit_on_success
def doturn():
  #print "start query --> " + str(len(connection.queries))
  random.seed()
  reports = {}
  info = {}
  prices = {}
  doclearinview()
  doatwar(reports,info,prices)
  doplanets(reports,prices)
  cullfleets(reports)
  dofleets(reports,prices)
  dobuildinview2()
  doplanetarydefense(reports)
  doencounters(reports)
  sendreports(reports)
  #print "end query --> " + str(len(connection.queries))


def doplanetarydefense(reports):
  """
  >>> random.seed(0)
  >>> buildinstrumentalities()
  >>> s = Sector(key=255123,x=100,y=100)
  >>> s.save()
  >>> u = User(username="doplanetarydefense")
  >>> u.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p = Planet(resources=r, society=75,owner=u, sector=s,
  ...            x=1275.5, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p.calculatesenserange()
  1.25
  >>> p.save()
  >>> pl = Player(user=u, capital=p, color=112233)
  >>> pl.lastactivity = datetime.datetime.now()
  >>> pl.save()

  >>> u2 = User(username="doplanetarydefense2")
  >>> u2.save()
  >>> p2 = Planet(resources=r, society=75,owner=u2, sector=s,
  ...            x=1277.5, y=617, r=.1, color=0x1234, name="Planet Y")
  >>> p2.save()
  >>> pl2 = Player(user=u2, capital=p2, color=112233)
  >>> pl2.lastactivity = datetime.datetime.now()
  >>> pl2.save()
  >>> pl2.setpoliticalrelation(pl,'enemy')
  >>> f = Fleet(owner=u2, sector=s, x=1275.0, y=617, cruisers=100, destroyers=100)
  >>> f.save()
  >>> fid = f.id
  >>> doclearinview()
  >>> dobuildinview2()
  >>> report = {u.id:[],u2.id:[]}

  >>> # no defenses
  >>> doplanetarydefense(report)
  >>> f.destroyers
  100
  >>> f.cruisers
  100

  >>> # defenses, too far
  >>> f.x = 1279.6
  >>> f.save()
  >>> p.startupgrade(Instrumentality.MATTERSYNTH1)
  >>> p.setupgradestate(Instrumentality.MATTERSYNTH1)
  >>> p.startupgrade(Instrumentality.PLANETARYDEFENSE)
  >>> p.setupgradestate(Instrumentality.PLANETARYDEFENSE)
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  100
  >>> f.cruisers
  100

  >>> #kaboom!
  >>> f.x = 1279.4
  >>> f.save()
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  90
  >>> f.cruisers
  98
  >>> pprint(report)
  {3: [u'Planetary Defenses: Engaged! -- Planet X (3) -- Fleet #3 owned by: doplanetarydefense2',
       'Planetary Defenses: before: 100 destroyers, 100 cruisers',
       'Planetary Defenses: after: 90 destroyers, 98 cruisers'],
   4: [u'Planetary Defenses: Encountered!  Fleet #3 -- attacked by Planet: Planet X (3) owned by: doplanetarydefense',
       'Planetary Defenses: before: 100 destroyers, 100 cruisers',
       'Planetary Defenses: after: 90 destroyers, 98 cruisers']}
  
  >>> f.x = 1275.4
  >>> f.save()
  >>> report = {u.id:[],u2.id:[]}
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  71
  >>> f.cruisers
  78
  >>> pprint(report)

  """
  users = User.objects.filter(planet__planetupgrade__instrumentality__type=Instrumentality.PLANETARYDEFENSE, 
                              planet__planetupgrade__state=PlanetUpgrade.ACTIVE, 
                              player__enemies__isnull=False).distinct()
  for u in users:
    replinestart = "Planetary Defenses: "
    planets = Planet.objects.filter(owner=u,
                                    planetupgrade__instrumentality__type=Instrumentality.PLANETARYDEFENSE,
                                    planetupgrade__state=PlanetUpgrade.ACTIVE)
    enemies = u.get_profile()\
               .enemies.all()\
               .values_list('user__id', flat=True)\
               .distinct().select_related('owner')

    fleets  = u.inviewof\
               .filter(owner__in=enemies)\
               .distinct()\
               .select_related('owner')

    if not reports.has_key(u.id):
      reports[u.id]=[]
    preport = reports[u.id]
    for p in planets.iterator():
      for f in fleets:
        # don't use iterator for fleets, because fleets can get
        # hit multiple times.
        gothit = False
        distance = getdistanceobj(p,f) 
        if distance < 4.0:
          freport = reports[f.owner.id]
          preport.append(replinestart+"Engaged! -- "+p.name+" ("+str(p.id)+") -- Fleet #" \
                         +str(f.id)+" owned by: "+f.owner.username)
          freport.append(replinestart+"Encountered!  Fleet #"+str(f.id)+" -- attacked by Planet: "+ \
                         p.name+" ("+str(p.id)+") owned by: "+p.owner.username)
          ships = f.shiplist()
          hitchance = .05 + (.15 - (.15 * math.log(1.0+distance,5.0)))
          #print "hitchance=" + str(hitchance)
          for st in ships:
            numships = ships[st]
            for i in xrange(numships):
              if random.random() < hitchance:
                numships -= 1
                if not gothit:
                  preport.append(replinestart+"before: " + f.shiplistreport())
                  freport.append(replinestart+"before: " + f.shiplistreport())
                  gothit = True
            setattr(f,st,numships)
          if gothit:
            if f.numships():
              f.damaged=True
            else:
              f.destroyed=True
            preport.append(replinestart+"after: " + f.shiplistreport())
            freport.append(replinestart+"after: " + f.shiplistreport())
          else:
            preport.append("no hits.")
            freport.append("no hits.")
          f.save()





@print_timing
def doatwar(reports, info,prices):
  prices['atwar'] = {}
  atwar = User.objects.filter(player__enemies__isnull=False).distinct()
  for user in atwar:
    prices['atwar'][user.id] = {}
    if not reports.has_key(user.id):
      reports[user.id]=[]
    reports[user.id].append("WAR! -- you are at war with the following players:")
    for enemy in user.get_profile().enemies.all():
      prices['atwar'][user.id][enemy.user_id] = 1
      reports[user.id].append("  " + enemy.user.username)

@print_timing
def doplanets(reports, prices):
  # do planets update
  planets = Planet.objects.\
                  filter(owner__isnull=False).\
                  select_related('owner', 'resources')
  for planet in planets.iterator():
    if not reports.has_key(planet.owner.id):
      reports[planet.owner.id]=[]

    planet.doturn(reports[planet.owner.id],prices)

@print_timing
def cullfleets(reports):
  # cull fleets...
  print "---"
  print "Culling Fleets"

  print "Num Destroyed = " + str(Fleet.objects.filter(destroyed=True).count())
  Fleet.objects.filter(destroyed=True).delete()

  print "Num Damaged = " + str(Fleet.objects.filter(damaged=True).count())
  Fleet.objects.filter(damaged=True).update(damaged=False)

  # spin through and remove all empty fleets (colony fleets that colonized, etc...)
  # should be able to do this inside the db with another couple flags... (see
  # above destroyed/damaged flags...)
  fleets = Fleet.objects.all()
  for fleet in fleets:
    if fleet.numships() == 0:
      print "deleting fleet #" + str(fleet.id)
      fleet.delete()
  print "---"

@print_timing
def dofleets(reports, prices):
  fleets = Fleet.objects.all().select_related('source', 'source__owner',
                                              'destination', 'destination__owner',
                                              'destination__resources',
                                              'homeport', 'homeport__owner',
                                              'owner','trade__manifest', 'route')

  for fleet in fleets.iterator():
    if not reports.has_key(fleet.owner.id):
      reports[fleet.owner.id]=[]
    if fleet.destination and fleet.destination.owner:
      if not reports.has_key(fleet.destination.owner_id):
        reports[fleet.destination.owner_id]=[]
      fleet.doturn(reports[fleet.owner_id],
                   reports[fleet.destination.owner_id],
                   prices)
    else:
      blah = []
      fleet.doturn(reports[fleet.owner_id],blah,prices)
  
@print_timing
def doencounters(reports):
  encounters = {}
  fleets = Fleet.objects.filter(viewable__isnull=False).order_by('?')
  for f in fleets.iterator():
    for otherfleet in f.viewable.all():
      if not reports.has_key(otherfleet.owner_id):
        reports[otherfleet.owner_id]=[]
      if not reports.has_key(f.owner_id):
        reports[f.owner.id]=[]
      encounterid = '-'.join([str(x) for x in sorted([f.id,otherfleet.id])]) 
      if encounters.has_key(encounterid):
        continue
      encounters[encounterid] = 1
      if otherfleet.owner_id == f.owner_id:
        continue
      else:
        doencounter(f,
                    otherfleet,
                    reports[f.owner_id],
                    reports[otherfleet.owner_id])

@print_timing
def sendreports(reports):
  for report in reports:
    user = User.objects.get(id=report)
    player = user.get_profile()
    
    if len(reports[report]) == 0:
      player.lastreport = "Nothing to report."
      player.save()
      continue
    fullreport = "\n".join(reports[report])
    fullreport = fullreport.encode('utf8')
    player.lastreport = fullreport
    player.save()

    if (datetime.datetime.now() - user.date_joined).days > 5:
      fullreport += "\n\n\n"
      fullreport += "---\n"
      fullreport += "If you do not wish to recieve email turn reports,\n"
      fullreport += "you can turn them off in the preferences panel\n"
      fullreport += "within the game.\n\n"
      fullreport += "Thanks for Playing! -- davesgalaxy.com\n"

    
    print "PLAYER #" + str(report) + " (" + user.username + ") REPORT:"
    print "-----------------------------------------------"
    print fullreport

    print user.email 
    
    if newdominion.settings.DEBUG == False and player.emailreports == True:
      send_mail("Dave's Galaxy Turn Report", 
                fullreport, 
                'turns@davesgalaxy.com', 
                [user.email])
    else:
      print "(test)"
  print "-- successful end of turn --"


if __name__ == "__main__":
  starttime = time.time()
  if len(sys.argv) == 2 and sys.argv[1] in ['--test','-t','--t','test','-test']:
    import doctest
    from django.test.utils import setup_test_environment
    from django.test.utils import teardown_test_environment
    from django.db import connection
    from django.conf import settings
    verbosity = 1
    interactive = True
    setup_test_environment()


    settings.DEBUG = False    
    old_name = settings.DATABASE_NAME
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)

    doctest.testmod()

    connection.creation.destroy_test_db(old_name, verbosity)
    teardown_test_environment()

    exit()

  doturn()
  
  endtime = time.time()
  elapsed = endtime-starttime
  print "Elapsed: " + str(elapsed) + "s"
