"""Render an interaction-style product demo for the live-tested AnnSetu workflow."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 30
OUT = Path(__file__).with_name("AnnSetu_Interactive_Demo.mp4")
REG, BOLD = "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"

def ft(n, b=False): return ImageFont.truetype(BOLD if b else REG, n)
def base(title, user=""):
    im = Image.new("RGB", (W,H), "#f5f8fb"); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,58), fill="#0d5c3b"); d.text((34,15),"AS  AnnSetu",font=ft(25,True),fill="white")
    d.text((W-260,18), user, font=ft(17), fill="#dcfce7")
    d.rectangle((0,58,230,H),fill="#123d31")
    for i,x in enumerate(["Dashboard","Book Slot","Gate Entry","Queue Manager","Transactions","Analytics"]):
        d.text((28,105+i*52),x,font=ft(17, i==0),fill="#ffffff" if i==0 else "#b9d4c7")
    d.text((270,93),title,font=ft(32,True),fill="#153447")
    return im,d
def box(d, xy, label, value="", active=False):
    x,y,w,h=xy; d.rounded_rectangle((x,y,x+w,y+h),12,fill="white",outline="#22a06b" if active else "#d5e1e8",width=3 if active else 2)
    d.text((x+16,y+10),label,font=ft(14,True),fill="#537080"); d.text((x+16,y+34),value,font=ft(20),fill="#16364b")
def button(d,xy,label):
    x,y,w,h=xy; d.rounded_rectangle((x,y,x+w,y+h),11,fill="#169b61"); d.text((x+18,y+13),label,font=ft(18,True),fill="white")
def cursor(d,x,y):
    d.polygon([(x,y),(x+5,y+25),(x+12,y+17),(x+21,y+31),(x+28,y+26),(x+18,y+13),(x+31,y+11)],fill="#111827",outline="white")
def intro():
    im=Image.new("RGB",(W,H),"#073625");d=ImageDraw.Draw(im)
    d.text((94,145),"ANNSETU",font=ft(64,True),fill="#63e6a1");d.text((98,235),"A transparent digital procurement journey",font=ft(34,True),fill="white")
    d.text((98,300),"From farmer slot booking to verified payment",font=ft(24),fill="#c9e8d8")
    d.rounded_rectangle((98,395,1110,515),24,fill="#0f5038"); d.text((145,430),"Live workflow:  BOOK  →  QUEUE  →  QUALITY  →  PAYMENT",font=ft(27,True),fill="white")
    return im
def login(t):
    im=Image.new("RGB",(W,H),"#effaf3");d=ImageDraw.Draw(im);d.rounded_rectangle((350,85,930,650),22,fill="white",outline="#d8e8de",width=2)
    d.text((468,140),"Login to AnnSetu",font=ft(35,True),fill="#143d2e");d.text((468,188),"Farmer portal",font=ft(20),fill="#557067")
    mob="9876543210"[:min(10,t)]; pw="farmer123"[:min(9,max(0,t-10))]
    box(d,(430,255,420,78),"MOBILE NUMBER",mob, t<10);box(d,(430,355,420,78),"PASSWORD","•"*len(pw),t>=10)
    button(d,(430,475,420,58),"Login as Farmer");cursor(d,770,505 if t>=19 else 390)
    return im
def booking(step):
    im,d=base("Book a Procurement Slot","Ranjit Singh • Farmer")
    d.text((270,145),"Step 5 of 6  •  Choose a convenient time",font=ft(19),fill="#537080")
    for i,(name,sub) in enumerate([("Crop","Cotton • MSP ₹7,121/Q"),("Quantity","12.5 quintals"),("Mandi","Agra Central Mandi"),("Date","Tomorrow")]):
        box(d,(290,195+i*72,420,57),name,sub)
    d.text((755,195),"Available time slots",font=ft(22,True),fill="#153447")
    for i,s in enumerate(["09:00 – 09:20","09:20 – 09:40","09:40 – 10:00"]):
        sel=i==0 and step>0; d.rounded_rectangle((755,240+i*70,1090,295+i*70),10,fill="#e6f8ee" if sel else "white",outline="#1fa366" if sel else "#d5e1e8",width=3 if sel else 2);d.text((780,257+i*70),s,font=ft(18,sel),fill="#12623e")
    button(d,(755,490,260,58),"Confirm Booking")
    cursor(d,870,260) if step == 0 else cursor(d,885,515)
    return im
def token():
    im,d=base("Booking confirmed","Ranjit Singh • Farmer");d.rounded_rectangle((350,165,1080,570),20,fill="white",outline="#bdebd1",width=3)
    d.text((562,205),"✓ Slot successfully booked",font=ft(30,True),fill="#14834f");d.text((555,270),"YOUR PROCUREMENT TOKEN",font=ft(16,True),fill="#537080");d.text((555,305),"COT-00003",font=ft(46,True),fill="#0d5c3b")
    d.rectangle((410,280,525,395),fill="#111827");
    for x in range(420,515,19):
        for y in range(290,385,19):
            if (x*y)%3: d.rectangle((x,y,x+11,y+11),fill="white")
    d.text((555,382),"Agra Central Mandi",font=ft(23,True),fill="#16364b");d.text((555,420),"Tomorrow • 09:00 AM • 12.5 Q",font=ft(20),fill="#537080");button(d,(555,465,270,55),"View My Dashboard")
    return im
def gate():
    im,d=base("Gate Entry","Amit Sharma • Mandi Staff");d.text((290,145),"Verify farmer token at the mandi entrance",font=ft(19),fill="#537080");box(d,(300,205,520,82),"TOKEN NUMBER","COT-00003",True);button(d,(845,217,185,55),"Search")
    d.rounded_rectangle((300,330,1030,565),18,fill="white",outline="#bdebd1",width=3);d.text((335,365),"✓ Valid booking — Farmer arrived",font=ft(27,True),fill="#15834e")
    for i,x in enumerate(["Farmer: Ranjit Singh","Crop: Cotton","Declared: 12.5 Q","Slot: 09:00 AM"]): d.text((340+(i%2)*330,425+(i//2)*48),x,font=ft(19),fill="#29485a")
    button(d,(730,495,245,53),"Mark Gate Entry");cursor(d,850,515);return im
def queue():
    im,d=base("Live Queue Manager","Amit Sharma • Mandi Staff");d.text((290,145),"Real-time queue updates",font=ft(19),fill="#537080")
    d.rounded_rectangle((290,195,1030,335),18,fill="#e9f9f0",outline="#79c99f",width=2);d.text((325,220),"NOW CALLED",font=ft(16,True),fill="#16824e");d.text((325,252),"Ranjit Singh   •   COT-00003",font=ft(29,True),fill="#153447");d.text((325,295),"Cotton • 12.5 Q • proceed to transaction desk",font=ft(18),fill="#537080")
    d.text((300,385),"Waiting queue",font=ft(23,True),fill="#153447")
    for i in range(3): box(d,(300,425+i*58,700,47),f"#{i+2}",f"Farmer {i+2}  •  estimated wait {(i+1)*20} min")
    cursor(d,620,270);return im
def transaction(stage):
    im,d=base("Transaction Entry","Amit Sharma • Mandi Staff");d.text((290,145),"COT-00003  •  Ranjit Singh  •  Cotton",font=ft(20),fill="#537080")
    for i,label in enumerate(["1  Quality Check","2  Weighment","3  Confirm & Pay"]):
        d.rounded_rectangle((290+i*250,190,515+i*250,240),10,fill="#e6f8ee" if i<=stage else "#edf2f5");d.text((305+i*250,207),label,font=ft(16,True),fill="#137446" if i<=stage else "#667b88")
    if stage==0:
        box(d,(330,300,260,75),"MOISTURE (%)","11.2",True);box(d,(630,300,260,75),"FOREIGN MATTER (%)","0.4");button(d,(500,445,260,55),"Save Quality: Accepted");cursor(d,520,340)
    else:
        box(d,(330,300,260,75),"GROSS WEIGHT (Q)","13.2",True);box(d,(630,300,260,75),"TARE WEIGHT (Q)","0.7");d.text((430,415),"Net weight calculated: 12.5 Q",font=ft(25,True),fill="#128350");button(d,(500,475,260,55),"Save Weighment");cursor(d,520,340)
    return im
def payment():
    im,d=base("Approval & Payment","Rajesh Gupta • Mandi Officer");d.rounded_rectangle((315,190,1010,545),20,fill="white",outline="#bdebd1",width=3)
    d.text((360,230),"Procurement approved",font=ft(30,True),fill="#15834e");d.text((360,285),"Cotton • Net quantity 12.5 Q",font=ft(21),fill="#345464");d.text((360,325),"MSP payment: ₹89,012.50",font=ft(30,True),fill="#153447")
    d.rounded_rectangle((360,390,950,470),13,fill="#e8faf0");d.text((390,410),"✓ Mock PFMS payment completed",font=ft(23,True),fill="#147d4a");d.text((390,442),"Status: PAID    •    UTR generated",font=ft(18),fill="#376b52");cursor(d,780,430);return im
def govt():
    im,d=base("Government Procurement Dashboard","Dr. A.K. Singh • Govt Admin")
    for i,(n,l,c) in enumerate([("3","Farmers","#e8f1ff"),("5","Active Mandis","#e9faf0"),("1","Anomaly Flag","#fff3e5")]):
        x=290+i*250;d.rounded_rectangle((x,180,x+220,285),15,fill=c);d.text((x+22,200),n,font=ft(37,True),fill="#153447");d.text((x+22,250),l,font=ft(17,True),fill="#537080")
    d.rounded_rectangle((290,325,760,580),16,fill="white",outline="#d5e1e8",width=2);d.text((320,350),"Procurement trend",font=ft(23,True),fill="#153447")
    for i,h in enumerate([60,100,75,150,190]): d.rectangle((350+i*65,535-h,390+i*65,535),fill="#1d9b64")
    d.rounded_rectangle((800,325,1100,580),16,fill="#fff8e9",outline="#ffd388",width=2);d.text((830,355),"Anomaly monitoring",font=ft(20,True),fill="#8c5513");d.text((830,405),"Centre flagged",font=ft(18),fill="#67502a");d.text((830,440),"Review queue & quality",font=ft(18),fill="#67502a")
    return im

scenes=[(intro(),3.5),(login(19),4),(booking(0),3),(booking(1),3),(token(),4),(gate(),4),(queue(),4),(transaction(0),4),(transaction(1),4),(payment(),4),(govt(),4)]
writer=cv2.VideoWriter(str(OUT),cv2.VideoWriter_fourcc(*"mp4v"),FPS,(W,H))
for im,secs in scenes:
    a=np.array(im); b=cv2.cvtColor(a,cv2.COLOR_RGB2BGR)
    for _ in range(int(secs*FPS)): writer.write(b)
writer.release();print(OUT)
