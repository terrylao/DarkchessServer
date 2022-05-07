"""
 * Protocol:
 * Board describe:
 * 1. horizontal 
 * 2. so has 8 columns, from A~H
 * 3. has 4 rows,from 1~4
 * Chess describe:
 * Empty place '-', 
 * Red King 'K', 帥
 * Red Guard 'G', 仕 
 * Red 'M', 相 
 * Red Rook 'R', 俥
 * Red Knight 'N', 傌
 * Red Cannon 'C', 炮
 * Red 'P', 兵
 * Black part 'k', 'g', 'm', 'r', 'n', 'c', 'p', 
 * not flip 'X'.

0 卒  1 包  2 馬  3 車  4 象  5 士  6 將
7 兵  8 炮  9 傌  10 俥  11 相  12 仕  13 帥
14 暗  15 空

全改成固定64 BYTES 長。right pad space

 * Server                     Client
Desk holder
<----------(J)oin[DeskName 30 bytes]------------//if deskname already, then join, else create a new desk
---(F)irst/(S)econd/(R)eject[for R only ERROR max 30 bytes, left shift right padding]--->  //Reject will close session
<---------(G)rant[Name max 20 bytes, left shift right padding]---------------
------(N)ame[Name max 20 bytes, left shift right padding]--------------->//opposite player name, and then waiting for server to call for Move
-----------Next Game(X)------------------------->Next Game
<-----------Next Game(X) accept-------------------------Next Game ready
----------(C)all------------->    //Call for Move
<-------(O)pen[A-H][1-4]/(M)ove[A-H][1-4][A-H][1-4]---
--------(O)pen[A-H][1-4][CHESS]/(M)ove[A-H][1-4][CHESS][A-H][1-4][CHESS]---/(I)nvalid------>  //O/M will broadcast, "I" only return to calli, after I, will send "C" again 
--------Yo(U)[(R)ed/(B)lack]----------> // to tell client which color they are
---------Yo(U)[(W)in/(L/T)ose/(D)raw]-------->//when one of player send U or has no more chess in board
-----------Next Game(X)------------------------->Next Game
<-----------Next Game(X) accept-------------------------Next Game ready
<---------(D)isconnect--------> //after receive D, just close session
<---------T(E)rminate--------> 

<---------R(D)raw-------------//draw game request
----------R(D)raw------------>
<---------AX/RX---------------//Accept or Reject

<---------R(L)ose-------------//lose game request
---------Yo(U)[(W)in/(L/T)ose]--------> //tell you win/lose to player

suddenly disconnect and reconnect:
<----------Jo(I)n------------
--------Transfer Last (B)oard State---------->//傳送現在的盤面,32byte board, 16bytes dead black, 16 bytes dead red
----(T)ransfer--->//Transfer for transfer the step action from start to last, it follow the command
----------(C)all------------->    //Call for Move if waiting for this client send move

"""
import socket, threading, signal, random, atexit, time, constant
LOCALHOST = "0.0.0.0"
PORT = 28008
deskHash={}
charmapper={'p':0,'c':1,'n':2,'r':3,'m':4,'g':5,'k':6,'P':7,'C':8,'N':9,'R':10,'M':11,'G':12,'K':13,'X':14,'-':15}
inversecharmapper={0:'p',1:'c',2:'n',3:'r',4:'m',5:'g',6:'k',7:'P',8:'C',9:'N',10:'R',11:'M',12:'G',13:'K',14:'X',15:'-'}
chinesemapper={0:'卒',1:'包',2:'馬',3:'車',4:'象',5:'士',6:'將',7:'兵',8:'炮',9:'傌',10:'俥',11:'相',12:'仕',13:'帥',14:'■',15:'□'}
is_exit=False
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((LOCALHOST, PORT))


class timecontrol(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.timerlist=[]
		self.Terminate=False
	def add2timer(self,adeskGame):
		self.timerlist.append(adeskGame)
	
	def removetimer(self,adeskGame):
		self.timerlist.remove(adeskGame)
		
	def terminate(self):
		self.Terminate=True
		
	def run(self):
		while not self.Terminate:
			time.sleep(2)
			for i in self.timerlist:
				if i.decTimer()==-1:
					self.timerlist.remove(i)
			
class deskGame():
	def __init__(self,holdersocket):
		self.sockets=[None,None]
		self.sockets[0] = holdersocket
		self.board = [[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS]]
		self.darkboard = [[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS]]
		self.logdarkboard = [[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS],
			[constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS,constant.BLANKCHESS]]
		self.deadChess=[[0,0,0,0,0,0,1,1,2,2,3,3,4,4,5,5,6],[0,7,7,7,7,7,8,8,9,9,10,10,11,11,12,12,13]];
		self.gaming=False
		self.freestep=0
		self.roundCount=3
		self.gameround=0
		self.colorside=[0,0]
		self.firstflip=False
		self.currentPlayer=0
		self.Xcount=0
		self.timers=[20,20]
		self.wincount=[0,0]
		self.ParticipantName=['-','-']
		self.gamelog=[]
		self.darkchesscount=32
	
	def setParticipant(self,participantsocket):
		if self.sockets[1]!=None:
			return 0
		self.sockets[1] = participantsocket
		self.sendTo(0,'F')
		self.sendTo(1,'S')
		return 1
		
	def checkInDesk(self,scoketid):
		if self.sockets[0]==None:
			return 0
		if self.sockets[0]==scoketid:
			return 1
		return 0
		
	def sendAll(self,msg):

		msg=msg.ljust(constant.PACKETSIZE, ' ')
		try:
			self.sockets[0].send(bytes(msg,'UTF-8'))
		except:
			self.sockets[0].close()
			try:
				msg='UW'
				msg=msg.ljust(constant.PACKETSIZE, ' ')
				self.sockets[1].send(bytes(msg,'UTF-8'))
				msg='E'
				msg=msg.ljust(constant.PACKETSIZE, ' ')
				self.sockets[1].send(bytes(msg,'UTF-8'))
				self.sockets[1].close();
			except:
				self.sockets[1].close();
		try:
			self.sockets[1].send(bytes(msg,'UTF-8'))
		except:
			self.sockets[1].close();
			try:
				msg='UW'
				msg=msg.ljust(constant.PACKETSIZE, ' ')
				self.sockets[0].send(bytes(msg,'UTF-8'))
				msg='E'
				msg=msg.ljust(constant.PACKETSIZE, ' ')
				self.sockets[0].send(bytes(msg,'UTF-8'))
				self.sockets[0].close();
			except:
				self.sockets[0].close();
		print("DEBUG:send all:",msg)

	
	def sendTo(self,who,msg):
		msg=msg.ljust(constant.PACKETSIZE, ' ')
		if who%2==0:
			try:
				self.sockets[0].send(bytes(msg,'UTF-8'))
			except:
				self.sockets[0].close()
				try:
					msg='UW'
					msg=msg.ljust(constant.PACKETSIZE, ' ')
					self.sockets[1].send(bytes(msg,'UTF-8'))
					msg='E'
					msg=msg.ljust(constant.PACKETSIZE, ' ')
					self.sockets[1].send(bytes(msg,'UTF-8'))
					self.sockets[1].close();
				except:
					self.sockets[1].close();
				return -1
		else:
			try:
				self.sockets[1].send(bytes(msg,'UTF-8'))
			except:
				self.sockets[1].close()
				try:
					msg='UW'
					msg=msg.ljust(constant.PACKETSIZE, ' ')
					self.sockets[0].send(bytes(msg,'UTF-8'))
					msg='E'
					msg=msg.ljust(constant.PACKETSIZE, ' ')
					self.sockets[0].send(bytes(msg,'UTF-8'))
					self.sockets[0].close();
				except:
					self.sockets[0].close();
				return -1
		print("DEBUG:send to:",who,"--",msg)
		return 0
		
	def printdarkboard(self):
		global chinesemapper
		print('--darkboard:')
		print('A B C D E F G H ')
		row=1
		for i in range(32):
			y=i//8
			x=i%8
			j=chinesemapper[self.darkboard[y][x]]
			print(j, end = '')
			if x>0 and x%7==0:
				print('-',row)
				row+=1

		
	def printboard(self):
		global chinesemapper
		print('--board:')
		print('A B C D E F G H ')
		row=1
		for i in range(32):
			y=i//8
			x=i%8
			j=chinesemapper[self.board[y][x]]
			print(j, end = '')
			if x>0 and x%7==0:
				print('-',row)
				row+=1
		print("--")
		print("captured:Black")
		for i in range(1,17):
			j=chinesemapper[self.deadChess[0][i]]
			print(j, end = '')
		print("\ncaptured:Red")
		for i in range(1,17):
			j=chinesemapper[self.deadChess[1][i]]
			print(j, end = '')
		print('')
		print('current Player:',self.currentPlayer,' player color:',self.colorside[self.currentPlayer])
		
	def setdarkboard(self,astring):
		global charmapper
		if len(astring)<65:
			return -1
		for i in range(1,17):
			self.deadChess[0][i]=constant.BLANKCHESS
			self.deadChess[1][i]=constant.BLANKCHESS
		self.deadChess[0][0]=0
		self.deadChess[1][0]=0
		
		for i in range(32):
			j=charmapper[astring[i]]
			y=i//8
			x=i%8
			self.board[y][x]=14
			self.darkboard[y][x]=j
			self.logdarkboard[y][x]=j
			
	def setboard(self,astring):
		global charmapper
		if len(astring)<65:
			return -1
		for i in range(1,17):
			self.deadChess[0][i]=constant.BLANKCHESS
			self.deadChess[1][i]=constant.BLANKCHESS
		self.deadChess[0][0]=0
		self.deadChess[1][0]=0
		
		for i in range(32):
			j=charmapper[astring[i]]
			y=i//8
			x=i%8
			self.board[y][x]=constant.BLANKCHESS
			self.darkboard[y][x]=constant.BLANKCHESS
			self.logdarkboard[y][x]=constant.BLANKCHESS
			self.board[y][x]=j
		
		for i in range(32,32+16):
			j=charmapper[astring[i]]
			self.deadChess[0][i-31]=j
			if j>0:
				self.deadChess[0][0]=self.deadChess[0][0]+1
			j=charmapper[astring[i+16]]
			self.deadChess[1][i-31]=j
			if j>0:
				self.deadChess[1][0]=self.deadChess[1][0]+1
		self.colorside=[0,1]
		self.currentPlayer=ord(astring[64])-ord('0')
		
	def startGame(self):
		self.clearboard()
		self.cap2board()
		self.shuffleBoard()
		self.printboard()
		self.freestep=0
		self.roundCount=3
		self.gameround+=1
		self.darkchesscount=32
		self.currentPlayer=1-(self.gameround%2)
		self.timers=[constant.GAMETIME,constant.GAMETIME]
		self.gaming=True
		print('DEBUG: startGame:gameround:',self.gameround,' currentPlayer:',self.currentPlayer)
		self.firstflip=True
		self.sendTo(self.currentPlayer,'C')
		self.printdarkboard()
		
	def getGameStatus(self):
		return self.gaming
	
	def clearboard(self):
		l=0;
		for j in range(2):
			for i in range(1,17):
				if self.board[l//8][l%8]==constant.BACKCHESS:
					self.capchess(self.logdarkboard[l//8][l%8])
				else:
					if self.board[l//8][l%8]!=constant.BLANKCHESS:
						self.capchess(self.board[l//8][l%8])
				l+=1

	def cap2board(self):
		l=0;
		for j in range(2):
			for i in range(1,17):
				self.logdarkboard[l//8][l%8]=self.deadChess[j][i]
				self.deadChess[j][i]=constant.BLANKCHESS
				self.board[l//8][l%8]=constant.BACKCHESS
				self.darkboard[l//8][l%8]=self.logdarkboard[l//8][l%8]
				l+=1
		self.deadChess[0][0]=0
		self.deadChess[1][0]=0
		
	def shuffleBoard(self):
		for i in range(1,10000):
			pos1=random.randint(0,31)
			pos2=random.randint(0,31)
			h1=pos1//8
			w1=pos1%8
			h2=pos2//8
			w2=pos2%8
			tmp=self.logdarkboard[h1][w1]
			self.logdarkboard[h1][w1]=self.logdarkboard[h2][w2]
			self.logdarkboard[h2][w2]=tmp
			tmp=self.darkboard[h1][w1]
			self.darkboard[h1][w1]=self.darkboard[h2][w2]
			self.darkboard[h2][w2]=tmp
			
		
	def canEat(self,posx1,posy1,posx2,posy2):
		chess1=self.board[posy1][posx1]#吃子的棋種
		chess2=self.board[posy2][posx2]#被吃得棋種
		print('canEat:',posx1,posy2,posx2,posy2,chess1,chess2)
		
		if (chess1//7==chess2//7):#顏色相同不能互吃
			print('same color')
			return False
			
		if abs(posx1-posx2)==1 or abs(posy1-posy2)==1:
			if chess2==constant.BLANKCHESS:
				return True
			
		if chess1==14 or chess2==14: #其中一方為暗子
			print('one dark chess')
			return False
		if (chess1==1 or chess1==8):
			if (posx1!=posx2) and (posy1!=posy2):
				print('cannon 1')
				return False

			if chess2==constant.BLANKCHESS:
				print('cannon 3')
				return False
				
			start=stop=jump=cnt=0
			if posx1==posx2:
				jump=8
			else:
				jump=1
			
			start=min(posy1*8+posx1,posy2*8+posx2)
			stop=max(posy1*8+posx1,posy2*8+posx2)
			print('start',start,'stop',stop,'jump',jump)
			for i in range(start+jump,stop,jump):
				print('board',i//8,i%8,'=',self.board[i//8][i%8])
				if self.board[i//8][i%8]!=constant.BLANKCHESS:
					cnt+=1
			if cnt!=1:
				print('cannon 4',cnt)
				return False
			else:
				return True
		else:
			if (chess1==13 and chess2==0) or (chess1==6 and chess2==7):#將不能吃兵，帥不能吃卒
				print('7 eat 1')
				return False
			elif (chess1==0 and chess2==13) or (chess1==7 and chess2==6):#兵吃將，卒吃帥
				return True
			elif (chess1%7)>=(chess2%7):
				return True
			else:
				print('all not')
				return False
	
	def cannonCheck(self,h1,w1):
		if h1==0:
			if w1==0:
				for i in range(1,8):
					if self.canEat(w1,h1,w1+i,h1):
						return 1
				for i in range(1,4):
					if self.canEat(w1,h1,w1,h1+i):
						return 1
			elif w1==7:
				for i in range(1,8):
					if self.canEat(w1,h1,w1-i,h1):
						return 1
				for i in range(1,4):
					if self.canEat(w1,h1,w1,h1+i):
						return 1
			else:
				for i in range(1,8-w1):
					if self.canEat(w1,h1,w1+i,h1):
						return 1
				for i in range(1,w1+1):
					if self.canEat(w1,h1,w1-i,h1):
						return 1
				for i in range(1,4-h1):
					if self.canEat(w1,h1,w1,h1+i):
						return 1
		elif h1==3:
			if w1==0:
				for i in range(1,8):
					if self.canEat(w1,h1,w1+i,h1):
						return 1
				for i in range(1,4):
					if self.canEat(w1,h1,w1,h1-i):
						return 1
			elif w1==7:
				for i in range(1,8):
					if self.canEat(w1,h1,w1-i,h1):
						return 1
				for i in range(1,4):
					if self.canEat(w1,h1,w1,h1-i):
						return 1
			else:
				for i in range(1,8-w1):
					if self.canEat(w1,h1,w1+i,h1):
						return 1
				for i in range(1,w1+1):
					if self.canEat(w1,h1,w1-i,h1):
						return 1
				for i in range(1,h1+1):
					if self.canEat(w1,h1,w1,h1-i):
						return 1
		else:
			if w1==0:
				for i in range(1,8-w1):
					if self.canEat(w1,h1,w1+i,h1):
						return 1
				for i in range(1,4-h1):
					if self.canEat(w1,h1,w1,h1+i):
						return 1
				for i in range(1,h1+1):
					if self.canEat(w1,h1,w1,h1-i):
						return 1
			elif w1==7:
				for i in range(1,w1+1):
					if self.canEat(w1,h1,w1-i,h1):
						return 1
				for i in range(1,4-h1):
					if self.canEat(w1,h1,w1,h1+i):
						return 1
				for i in range(1,h1+1):
					if self.canEat(w1,h1,w1,h1-i):
						return 1
			else:
				for i in range(1,8-w1):
					if self.canEat(w1,h1,w1+i,h1):
						return 1
				for i in range(1,w1+1):
					if self.canEat(w1,h1,w1-i,h1):
						return 1
				for i in range(1,4-h1):
					if self.canEat(w1,h1,w1,h1+i):
						return 1
				for i in range(1,h1+1):
					if self.canEat(w1,h1,w1,h1-i):
						return 1
		return 0
	#color 0=BLACK 1=RED
	def moveGen(self,color):
		r=0
		for i in range(32):
			h1=i//8
			w1=i%8
			if self.darkboard[h1][w1]>=0 and self.darkboard[h1][w1]<14:
				if self.darkboard[h1][w1]//7==color:
					return 1
			else:
				if self.board[h1][w1]>=0 and self.board[h1][w1]<14:
					if self.board[h1][w1]//7==color:
						print('moveGen:',h1,w1,self.board[h1][w1])
						if self.board[h1][w1]==1 or self.board[h1][w1]==8:
							r=self.cannonCheck(h1,w1)
							if r>0:
								return r
							continue
						if h1==0:
							if w1==0:
								if self.canEat(w1,h1,w1+1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1+1):
									return 1
							elif w1==7:
								if self.canEat(w1,h1,w1-1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1+1):
									return 1
							else:
								if self.canEat(w1,h1,w1+1,h1):
									return 1
								if self.canEat(w1,h1,w1-1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1+1):
									return 1
						
						elif h1==1 or h1==2:
							if w1==0:
								if self.canEat(w1,h1,w1+1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1+1):
									return 1
								if self.canEat(w1,h1,w1,h1-1):
									return 1
							elif w1==7:
								if self.canEat(w1,h1,w1-1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1+1):
									return 1
								if self.canEat(w1,h1,w1,h1-1):
									return 1
							else:
								if self.canEat(w1,h1,w1+1,h1):
									return 1
								if self.canEat(w1,h1,w1-1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1+1):
									return 1
								if self.canEat(w1,h1,w1,h1-1):
									return 1
								
						elif h1==3:
							if w1==0:
								if self.canEat(w1,h1,w1+1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1-1):
									return 1
							elif w1==7:
								if self.canEat(w1,h1,w1-1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1-1):
									return 1
							else:
								if self.canEat(w1,h1,w1+1,h1):
									return 1
								if self.canEat(w1,h1,w1-1,h1):
									return 1
								if self.canEat(w1,h1,w1,h1-1):
									return 1
		return r
					
	def doFlip(self,msg,resultList):
		global inversecharmapper
		posx=ord(msg[1])-ord('A')
		posy=ord(msg[2])-ord('1')
		if posx<0 or posx>8:
			print('DEBUG: FLIP posy',posx)
			return 0
			
		if posy<0 or posy>3:
			print('DEBUG: FLIP posy',posy)
			return 0
		if self.darkboard[posy][posx]==constant.BLANKCHESS:
			print('DEBUG: FLIP BLANKCHESS')
			return 0
		self.board[posy][posx]=self.darkboard[posy][posx]
		self.darkboard[posy][posx]=constant.BLANKCHESS
		resultList[0]=msg[0]
		resultList[1]=msg[1]
		resultList[2]=msg[2]
		resultList[3]=inversecharmapper[self.board[posy][posx]]
		self.freestep=0
		self.darkchesscount-=1
		r=1
		if self.board[posy][posx]>6:
			r=2
		return r
	
	def capchess(self,chess):
		if chess>=0 and chess<14:
			y=chess // 7
			self.deadChess[y][0]+=1
			self.deadChess[y][self.deadChess[y][0]]=chess
			self.freestep=0
		else:
			self.freestep+=1
				
			
	def doMove(self,msg,resultList):
		global inversecharmapper
		posx1=ord(msg[1])-ord('A')
		posy1=ord(msg[2])-ord('1')
		posx2=ord(msg[3])-ord('A')
		posy2=ord(msg[4])-ord('1')
		if posx1<0 or posx1>8:
			return 0
		if posx2<0 or posx2>8:
			return 0
		if posy1<0 or posy1>3:
			return 0
		if posy2<0 or posy2>3:
			return 0
		if self.canEat(posx1,posy1,posx2,posy2):
			resultList[0]=msg[0]
			resultList[1]=msg[1]
			resultList[2]=msg[2]
			resultList[3]=inversecharmapper[self.board[posy1][posx1]]
			resultList[4]=msg[3]
			resultList[5]=msg[4]
			resultList[6]=inversecharmapper[self.board[posy2][posx2]]
			self.capchess(self.board[posy2][posx2])
			self.board[posy2][posx2]=self.board[posy1][posx1]
			self.board[posy1][posx1]=constant.BLANKCHESS
		else:
			print('canEat return false')
			return 0
		return 1
	#in this time, server not change player yet
	def checkWin(self):
		print('DEBUG:checkWinner:',1-self.currentPlayer,self.deadChess[self.colorside[1-self.currentPlayer]][0])
		if self.deadChess[self.colorside[1-self.currentPlayer]][0]==16:
			print('DEBUG:checkWinner:all dead')
			self.sendTo(1-self.currentPlayer,'UL')
			self.sendTo(self.currentPlayer,'UW')
			self.wincount[self.currentPlayer]+=1
			self.doNextGame()
			return 1
		else:
			if self.freestep==60:
				print('DEBUG:checkWinner:draw game')
				self.sendTo(1,'UD')
				self.sendTo(0,'UD')
				self.doNextGame()
				return 1
		
		#if self.darkchesscount>0:
		#	return 0
		#check if some player cannot generate move.
		if self.moveGen(1-self.currentPlayer)==0:
			print('DEBUG:checkWinner:no moves')
			self.sendTo(1-self.currentPlayer,'UL')
			self.sendTo(self.currentPlayer,'UW')
			self.wincount[self.currentPlayer]+=1
			self.doNextGame()
			return 1
		return 0

	def forceLose(self):
		self.sendTo(self.currentPlayer,'UL')
		self.sendTo(1-self.currentPlayer,'UW')
		self.wincount[1-self.currentPlayer]+=1
		self.doNextGame()
		return 1
		
	def setParticipantName(self,partid,name):
		self.ParticipantName[partid-1]=name
		print('name length=',len(name))
		if partid==1:
			self.sendTo(1,'N'+name)
		else:
			self.sendTo(0,'N'+name)
			time.sleep(2.4)
			
		if self.ParticipantName[0]!='-' and self.ParticipantName[1]!='-':
			if partid==2:
				self.doNextGame()
		
	def doNextGame(self):
		self.gaming=False
		if (self.gameround>self.roundCount):
			self.sendAll('D')
			return 2
		self.sendAll('X')
		
	def decTimer(self):
		if self.gaming==True:
			self.timers[self.currentPlayer]-=1
			print('timer:',self.currentPlayer,self.timers[self.currentPlayer])
			if self.timers[self.currentPlayer]==-1:
				r=self.sendTo(self.currentPlayer,'UT')
				r1=self.sendTo(self.currentPlayer,'UW')
				if r==0 and r1==0:
					self.doNextGame()
					return 0
				else:
					return -1
			return 0
			
	def incX(self):
		self.Xcount+=1
		if self.Xcount==2:
			self.Xcount=0
			print('startGame at X')
			self.startGame()
	
	def writeLog(self,winuser):
		if winuser==0:
			filename=self.ParticipantName[0].strip()+'(WIN)_vs_'+self.ParticipantName[1].strip()+'_'+now.strftime("%Y%m%d%H%M%S")+'.txt'
		else:
			filename=self.ParticipantName[0].strip()+'_vs_'+self.ParticipantName[1].strip()+'(WIN)_'+now.strftime("%Y%m%d%H%M%S")+'.txt'
			
		with open(filename, 'w') as f:
			for i in range(32):
				y=i//8
				x=i%8
				f.write("%d,\n" % self.logdarkboard[y][x])
			for item in self.gamelog:
				f.write("%s\n" % item)
				
		self.gamelog.clear()
		
	def execute(self,fromuser,msg):
		print('DEBUG: execute:',fromuser,msg,' currentPlayer:',self.currentPlayer)
		if fromuser-1!=self.currentPlayer:
			return 0
		
		if msg[0]=='R':
			if msg[1]=='D':
				
				return 1
			else:
				if msg[1]=='L':
					self.forceLose()
					return 1
		resultlist=[]
		if msg[0]=='O':
			resultlist=['O','P','A','R']
			r=self.doFlip(msg,resultlist)
			if r>0:
				self.timers[self.currentPlayer]=constant.GAMETIME
				result=''.join(resultlist)
				self.gamelog.append(result)
				if self.firstflip:
					self.firstflip=False
					if r==1:
						self.sendTo(self.currentPlayer,'UB')
						self.sendTo(1-self.currentPlayer,'UR')
						self.colorside[self.currentPlayer]=0
						self.colorside[1-self.currentPlayer]=1
					else:
						self.sendTo(self.currentPlayer ,'UR')
						self.sendTo(1-self.currentPlayer,'UB')
						self.colorside[self.currentPlayer]=1
						self.colorside[1-self.currentPlayer]=0
					print('gameround at:',self.gameround,' colorside[0]=',self.colorside[0],' colorside[1]=',self.colorside[1])
			else:
				print('FLIP Error at:',resultlist,r)
				return 0
		else:
			if msg[0]=='M':
				resultlist=['M','P','A','R','A','M','E']
				r=self.doMove(msg,resultlist)
				if r>0:
					self.timers[self.currentPlayer]=constant.GAMETIME
					result=''.join(resultlist)
					self.gamelog.append(result)
				else:
					print('Move Error at:',resultlist,r)
					return 0
		self.sendAll(result)
		self.printboard()
		r=self.checkWin()
		if r>0:
			print('Score:0=',self.wincount[0],',',self.wincount[1])
			return r
		self.currentPlayer=1-self.currentPlayer;
		self.sendTo(self.currentPlayer,'C')
		return 1
		
class ClientThread(threading.Thread):
	def __init__(self,clientAddress,clientsocket):
		threading.Thread.__init__(self)
		self.csocket = clientsocket
		self.cAddress=clientAddress;
		#self.csocket.setsockopt( IPPROTO_TCP, TCP_NODELAY, 1 )
		self.deskname=''
		self.firsthand=0
		print ("New connection added: ", clientAddress)

	def run(self):
		global deskHash
		global is_exit
		global gameTimer
		print (threading.get_ident(),"Connection from : ", self.cAddress)
		#self.csocket.send(bytes("Hi, This is from Server..",'utf-8'))
		msg = ''
		self.loginDone=False
		self.connected=True
		zerotimes=0
		self.deskname=''
		while self.connected and is_exit==False:
			try:
				data = self.csocket.recv(constant.PACKETSIZE)
			except ConnectionResetError:
				print(self.cAddress,'DEBUG:ConnectionResetError')
				break
			except ConnectionAbortedError:
				print(self.cAddress,'DEBUG:ConnectionAbortedError')
				break	
			if not data:#means disconnected??
				print(self.cAddress,'DEBUG:data 0 disconnected:',zerotimes)
				zerotimes=zerotimes+1
				if zerotimes==3:
					if self.desk.getGameStatus()==True:
						self.desk.sendTo(1,'E')
					break;
				continue
			zerotimes=0
			if len(msg)==0:
				msg = data.decode()
			else:
				msg += data.decode()
			print(self.cAddress,'DEBUG:imcoming:',msg,len(msg))
			hasMore=True
			while len(msg)>0:
				if msg[0]=='J': #Join desk
					if len(msg)>30:
						key = msg[1:31]
						if key in deskHash:
							self.desk=deskHash[key]
							r=self.desk.setParticipant(self.csocket)
							if r==0:
								self.connected=False
								print('DEBUG:reject: ',key)
								self.csocket.send(bytes('Rdesk in playing'.ljust(constant.PACKETSIZE, ' '),'UTF-8'))
								break;
							self.firsthand=2
						else:
							self.desk=deskGame(self.csocket)
							
							gameTimer.add2timer(self.desk);
							self.deskname=msg[1:31]
							deskHash[self.deskname]=self.desk
							self.firsthand=1
						#msg=msg[31:]
						msg='';
						continue
					break

				if 	msg[0]=='G':#Name of Player
					if len(msg)>20:
						self.name=msg[1:21]
						self.loginDone=True;
						self.desk.setParticipantName(self.firsthand,self.name)
						#msg=msg[21:]
						msg='';
						continue
					break
				if msg[0]=='R':#Request for Draw/Lose
					if len(msg)>1:
						r=self.desk.execute(self.firsthand,msg[:2])
						msg='';
						continue
					break
				
				if msg[0]=='O':#Flip a chess
					if len(msg)>2:
						r=self.desk.execute(self.firsthand,msg[:3])
						if r==2:
							print('DEBUG:all game done')
							self.connected=False
							break
						#msg=msg[3:]
						msg='';
						#print('DEBUG:after O',len(msg))
						continue
					break
							
				
				if msg[0]=='M':#Move a chess
					if len(msg)>3:
						r=self.desk.execute(self.firsthand,msg[:5])
						if r==2:
							print('DEBUG:all game done')
							self.connected=False
							break
						#msg=msg[5:]
						msg='';
						#print('DEBUG:after M',len(msg))
						continue
					break
				
				if msg[0]=='X':
					msg=msg[1:]
					self.desk.incX()
					msg=''
					break
					
			#if self.loginDone==True and self.firsthand==1:
			#	if self.desk.getGameStatus()==False:
			#		self.loginDone=False
			#		print('startGame at Client Thread')
			#		self.desk.startGame()
					
#currentPlayer 誰控，換ROUND 時要換對。檢查無走步要做對
			#if msg=='bye':
			#  break
			#print ("from client", msg)
			#self.csocket.send(bytes(msg,'UTF-8'))
		self.csocket.close()
		print ("Client at ", clientAddress , " disconnected...")
		if self.firsthand==1:
			if self.deskname in deskHash:
				print ("remove desk ", self.deskname , " removed...")
				del deskHash[self.deskname]
		

def handler(signum, frame):
	global is_exit
	global server
	is_exit = True
	server.close
	print ("receive a signal ",signum, "is_exit = ", is_exit)
	sys.exit()
		
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
#signal.signal(signal.SIGBREAK, handler)
gameTimer=timecontrol()
gameTimer.start()
print("Server started")
print("Waiting for client request..")
try:
	while is_exit==False:
		server.listen(1)
		clientsock, clientAddress = server.accept()
		newthread = ClientThread(clientAddress, clientsock)
		newthread.start()
except:
	server.close

"""
#for testing
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
desk=deskGame(s)

#中間困死
desk.setboard('---p------pKp------p------------pccnnrrmmggk----PPPPPCCNNRRMMGG-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#中間困不死炮
desk.setboard('---p------pCp-n----p------------pccnrrmmggkk----PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red not Lose');

#右下角困死
desk.setboard('--------------r--------n------nCpppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#右上角困死
desk.setboard('------nC------rn----------------pppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#左上角困死
desk.setboard('Cn------n-----r-----------------pppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#左下角困死
desk.setboard('--------------r-n-------Cn------pppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#左下角困不死
desk.setboard('----------------n-------Cn----r-pppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red not Lose');

#下方困死
desk.setboard('-------------------r------nCn---pppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#上方困死
desk.setboard('--nCn------r--------------------pppppccrmmggk---PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#上方困不死
desk.setboard('--nCn------r-------k------------pppppccrmmgg----PPPPPCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red not Lose');

#黑吃光紅
desk.setboard('--n-n------r-------k------------pppppccrmmgg----PPPPPCCNNRRMMGGK0')
desk.printboard()
desk.checkWin()
print('Red should Lose');

#紅吃光黑
desk.setboard('----------K--------G------------pppppccnnrrmmggkPPPPPCCNNRRMMG--1')
desk.printboard()
desk.checkWin()
print('Black should Lose');

desk.setboard('--------------------m---n--rCn-Mpppppccrmggk----PPPPPCNNRRMGGK--0')
desk.printboard()
desk.checkWin()
print('Red not Lose');

desk.setboard('------------m---n--rCn-M----k---pppppccrmgg-----PPPPPCNNRRMGGK--0')
desk.printboard()
desk.checkWin()
print('Red not Lose');
desk.setboard('------------m---n--rMn------k---pppppccrmgg-----PPPPPCCNNRRMGGK-0')
desk.printboard()
desk.checkWin()
print('Red not Lose');
desk.setboard('------------m---n--rPn------k---pppppccrmgg-----PPPPCCNNRRMMGGK-0')
desk.printboard()
desk.checkWin()
print('Red not Lose');

#莫明無法走子?
desk.setboard('------c----C-K-M---GN-g--R-MXpgppppcnnrrmmk-----PPPPPCNR--------1')
desk.printboard()
desk.checkWin()

desk.setboard('XXXR-XXpXXXXXkXGXX-N-m--XXXXX-XPccn-------------MPM-------------1')
desk.printboard()
desk.execute(0,'OE2')
"""