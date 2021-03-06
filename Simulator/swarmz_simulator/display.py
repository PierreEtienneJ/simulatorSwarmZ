import pygame
from pygame import locals as const

import time
import threading
import statistics

from pygame.draw import rect

from swarmz_simulator.vector import Vector
from swarmz_simulator.object import Object
from swarmz_simulator.environment import Environment


class Display():
    """this class use pygame to display the simulation"""
    def __init__(self,environment:Environment, eventDisplay):
        """need one Surface and one simulation"""
        pygame.init()    
        self.screen=pygame.display.set_mode((1080,720), pygame.RESIZABLE) #taille modifiable
        self.environment=environment
        self.eventDisplay=eventDisplay

        self.size=self.screen.get_size()

        self.background=(20,20,150) #never use yet
        self.running = True

        #definition du zoom
        self.center=Vector(0,0)
        self.radius=0
        self.zoom=1
        
        self.zoom_auto() #à # si vous voulez pas utiliser le zoom auto
        
        self.clock= pygame.time.Clock()
        #sauvegarde des events 
        #pour déplacer le centre, clique gauche continue
        self.maintien_clique_gauche=False
        self.position_souris_avant=Vector(0,0)

        self.maintien_clique_droit=False
        self.new_clique_Object=[]
        self.ind_curentDrone=None
        
        self.pos_souris=[]

        self.displayRadar=False
        
        self.time=0
        self.fps=0
        self.stdFps=0

    def zoom_auto(self):
        """set new zoom
        """
        #recherche du barycenter des objets et des drones
        center=Vector(0,0)
        for drone in self.environment.drones:
            center.x+=drone.position.x
            center.y+=drone.position.y

        for obj in self.environment.objects:
            center.x+=obj.center.x
            center.y+=obj.center.y

        if(self.environment.nb_objects+self.environment.nb_drones!=0):
            center=center.x_scal(1/(self.environment.nb_objects+ self.environment.nb_drones))
        
        self.center=center
        
        #recherche du points le plus loin du centre
        radius=1
        for drone in self.environment.drones:
            if(self.center.distance(drone.position)>radius):
                radius=self.center.distance(drone.position)

        for obj in self.environment.objects:
            if(self.center.distance(obj.center)>radius):
                radius=self.center.distance(obj.center)
        
        self.radius=radius*1.2

        #def du zoom
        self.zoom=min(self.size)/2*1/self.radius 
    
    def __cliqueDrone(self, x,y):
        p=self.inv_offsetPoint((x,y))
        p=p.x_scal(1/self.zoom)
        for i,drone in enumerate(self.environment.drones):
            if(p.distance(drone.position)<drone.radius):
                return i
        return None
            
    def process_event(self, event:pygame.event):
        ##utilisation du zoom
        
        if(event.type == pygame.QUIT):
            self.running=False
        
        if(event.type == pygame.MOUSEBUTTONDOWN): #si on clique avec la souris
            if(event.button==1): #clique gauche
                x, y = event.pos #position de la souris
                ret=self.__cliqueDrone(x,y)
                if(ret!=None):
                    self.ind_curentDrone=ret
                else:
                    self.ind_curentDrone=None
                    self.maintien_clique_gauche=True
                    
                    self.position_souris_avant=Vector(x,y) #sauvegarde

            if(event.button==3): #clique droit
                self.maintien_clique_droit=True
                x, y = event.pos #position de la souris
                #p_y=
                self.new_clique_Object.append(self.inv_offsetPoint((x,y)).x_scal(1/self.zoom))

            if(event.button==4): #Molette souris haut

                self.zoom+=2   #on zoom
                
                self.center=self.center.x_scal((self.zoom+2)/(self.zoom))
            if(event.button==5): #Molette souris bas
                self.zoom-=2   #on dezoom
                if(self.zoom<1):
                    self.zoom=1
                    
                self.center=self.center.x_scal(self.zoom/(self.zoom+2))

        if(event.type == pygame.MOUSEBUTTONUP): # si on declique
            if(event.button==1): #clique gauche
                self.maintien_clique_gauche=False
            
            if(event.button==3): #clique droit
                self.maintien_clique_droit=False

        if(event.type==pygame.MOUSEMOTION): #si la souris bouge
            self.pos_souris=event.pos
            if(self.maintien_clique_gauche): #si le clique gauche est tjrs enfoncé
                x, y = event.pos #position souris
                delta=self.position_souris_avant.add(Vector(x,y).x_scal(-1)) #delta=avant-après

                self.center=self.center.add(delta.x_scal(-1))  #centre=centre-delta
                self.position_souris_avant=Vector(x,y)

        if(event.type==pygame.KEYDOWN): #si on apuye sur une touche clavier
            if(event.key==pygame.K_SPACE): #espace
                if(self.eventDisplay.pause): #si on était en pause on enlève
                    self.eventDisplay.pause=False
                else: #si on était pas en pause on met pause
                    self.eventDisplay.pause=True
            
            if(event.key==const.K_q):
                self.stop()
            if(event.key==const.K_p):
                self.zoom+=2   #on zoom
            if(event.key==const.K_m):
                self.zoom-=2   #on dezoom
                if(self.zoom<1):
                    self.zoom=1
                
            if(event.key==const.K_a):
                if(self.displayRadar):
                    self.displayRadar=False
                else:
                    self.displayRadar=True

            if(event.key==const.K_PLUS or event.key==const.K_KP_PLUS or event.key==const.K_EQUALS):
                self.eventDisplay.coefTime*=1.2
                if(self.eventDisplay.coefTime>15):
                    self.eventDisplay.coefTime=15

            if(event.key==const.K_MINUS or event.key==const.K_KP_MINUS or event.key==54): #54=minus key
                self.eventDisplay.coefTime*=0.8
            
            if(event.key == const.K_ESCAPE): #on appuye sur echap => annule le polygone
                self.new_clique_Object=[]
            if(event.key == const.K_RETURN): #sur enter on confirme le polygone
                if(len(self.new_clique_Object)>1):
                    self.environment.addObject(self.new_clique_Object)
                self.new_clique_Object=[]

        if(event.type == pygame.QUIT):
            self.stop()
            
    def offset(self, a): #def décalage par rapport au centre de la fenètre
        x,y=a
        x=x+self.center.x+self.size[0]/2
        y=-y+self.center.y+self.size[1]/2
        return (x,y)

    def inv_offset(self, a): #inversion du décalage par rapport au centre de la fenetre
        x,y=a
        x=x-(self.center.x+self.size[0]/2)
        y=-y+self.center.y+self.size[1]/2
        return (x,y)
    
    def inv_offsetPoint(self,a):
        (x,y)=self.inv_offset(a)
        return Vector(x,y)

    def offset_Point(self, p): #espèce de sur-définition
        return self.offset((p.x, p.y))

    def update_screen(self, **kwargs):
        pygame.draw.rect(self.screen, self.background, (0,0)+self.size) #recrée un fond
        
           #dessine l'absice et l'ordonnée
        pygame.draw.line(self.screen, (255,0,0),self.offset((0,-1e4)), self.offset((0, 1e4)))
        pygame.draw.line(self.screen, (255,0,0),self.offset((-1e4,0)), self.offset((1e4, 0)))
            
        #on dessine le but : 
        if(self.environment.goal_has_def()):
            P=[]
            for p in self.environment.goal.list_Points:
                P.append(self.offset_Point(p.x_scal(self.zoom)))
            pygame.draw.polygon(self.screen, (255,0,0), P,0)
                
            #dessine les obstacles
        for obj in self.environment.objects:
            points=obj.list_Points
            P=[]
            for point in points:
                P.append(self.offset_Point(point.x_scal(self.zoom)))
            pygame.draw.polygon(self.screen, (255,255,255), P,7)
            
            #draw all drones by circle 
    
        for i,drone in enumerate(self.environment.drones):
            
            #    pygame.draw.circle(self.screen, (255,0,255), self.offset_Point(drone.position.x_scal(self.zoom)), drone.radius*self.zoom)
            a=drone.radius
            b=drone.radius
            p=[Vector(-a/2,b/2),Vector(-a/2,-b/2),Vector(a/4,-b/2), Vector(a/1.5,0), Vector(a/4,b/2)]
            P=[]
            for e in p:
                e.setCap(drone.getCap()+e.cap())
                e=drone.position.add(e).x_scal(self.zoom)
                P.append(self.offset_Point(e))
            if(i==self.ind_curentDrone):
                pygame.draw.polygon(self.screen, (200,100,100), P,5)
            else:
                pygame.draw.polygon(self.screen, drone.color, P,5)

                #draw radar
            if(self.displayRadar or self.ind_curentDrone==i):
                for j in range(drone.radar.nb_rays):
                    ray=Vector(1,0)
                    ray.setCap(drone.radar.angles_[j]+drone.getCap())
                    ray.setNorm(drone.radar.rays[j])
                    pygame.draw.line(self.screen, (0,200,0), self.offset_Point(drone.position.x_scal(self.zoom)), 
                                    self.offset_Point(drone.position.add(ray).x_scal(self.zoom)), 1)
                
                    
    
                #drow speed vector
            pygame.draw.line(self.screen, (255,0,0), self.offset_Point(drone.position.x_scal(self.zoom)), 
                                 self.offset_Point(drone.position.add(drone.speed).x_scal(self.zoom)), 2)

            cap=Vector(1,0)
            cap.setCap(drone.getCap())
            pygame.draw.line(self.screen, (0,0,255), self.offset_Point(drone.position.x_scal(self.zoom)), 
                                 self.offset_Point(drone.position.add(cap).x_scal(self.zoom)), 2)
            capCo=Vector(1,0)
            capCo.setCap(drone.capCommande)
            pygame.draw.line(self.screen, (0,0,0), self.offset_Point(drone.position.x_scal(self.zoom)), 
                                 self.offset_Point(drone.position.add(capCo).x_scal(self.zoom)), 2)

            motor=drone.motorPower.copy()
            motor.setNorm(drone.motorPower.norm_2()/5)
            motor.setCap(drone.getCap()+motor.cap()-3.1415)

            motor_init=Vector(drone.positionOfRudder, 0)
            motor_init.setCap(drone.getCap()-3.1415)
            motor_init=motor_init.add(drone.position)

            pygame.draw.line(self.screen, (255,0,0), self.offset_Point(motor_init.x_scal(self.zoom)), 
                                 self.offset_Point(motor_init.add(motor).x_scal(self.zoom)), 2)
            
            
        if(self.eventDisplay.pause):
            police = pygame.font.Font(None,60)
            texte = police.render("Pause",True,pygame.Color("#FFFF00"))
            a,b=texte.get_size()
            self.screen.blit(texte, (self.size[0]/2-a/2, (self.size[1]-b)/3))

        #on dessine le polygone en cours
        if(len(self.new_clique_Object)>0):
            P=[]
            for point in self.new_clique_Object:
                P.append(self.offset_Point(point.x_scal(self.zoom)))
            P.append(self.pos_souris)
            pygame.draw.lines(self.screen, (255,255,255), False, P,2)
        
        ##dessine le temps
        police = pygame.font.Font(None,35)
        minu=str(int(self.time//60))
        sec=str(int(self.time%60))
        if(len(minu)==1):
            minu="0"+minu
        if(len(sec)==1):
            sec="0"+sec
        texte = police.render(str(minu)+":"+str(sec),True,pygame.Color("#FFFF00"))
        a,b=texte.get_size()
        self.screen.blit(texte, (0, 0))

        ##dessine le coef time
        texte = police.render("x"+str(int(self.eventDisplay.coefTime*10)/10),True,pygame.Color("#FFFF00"))
        self.screen.blit(texte, (a*1.2, 0))

        #dessine zoom :
        texte = police.render("zoom : "+str(int(self.zoom)),True,pygame.Color("#FFFF00"))
        self.screen.blit(texte, (0, b*1.2))
        
        #FPS:
        fps=str(int(self.fps*10)/10)
        if(len(fps)<4):
            fps="0"+fps
        
        stdfps=str(int(self.stdFps*10)/10)
        if(len(fps)<4):
            stdfps="0"+stdfps
        texte = police.render("FPS : "+fps+"+-"+stdfps,True,pygame.Color("#FFFF00"))
        a,b=texte.get_size()
        c,d=self.size
        self.screen.blit(texte, (c-a, 0))
        
        
        ########################
        ##history 
        #####################
        if(self.ind_curentDrone!=None):
            (a,b)=self.size
            c,d=a*0.7, b*0.8
            pygame.draw.polygon(self.screen, (200, 200,200), [(a,b), (a, d), (c, d), (c, b)],0)
            
            police = pygame.font.Font(None,20)
            texte = police.render(self.environment.drones[self.ind_curentDrone].name,True,(25, 25, 25))
            e,f=texte.get_size()
            self.screen.blit(texte, (c,d))
            texte = police.render("speed : "+str(int(self.environment.drones[self.ind_curentDrone].speed.norm_2()*100)/100),True,(0, 255, 25))
            self.screen.blit(texte, (c+e*1.2,d))
            
            time_ms=str(int((self.environment.drones[self.ind_curentDrone].time%60*100)))
            time_s=str(int((self.environment.drones[self.ind_curentDrone].time%60)))
            time_ms=time_ms[len(time_s):]
            time=str(int(self.environment.drones[self.ind_curentDrone].time//60))
            if(len(time)<2):
                time="0"+time
            if(len(time_s)<2):
                time_s="0"+time_s
            if(len(time_ms)<2):
                time_ms="0"+time_ms
            
            texte = police.render("time : "+time+":"+time_s+"''"+time_ms,True,(50, 50, 50))
            g,h=texte.get_size()
            self.screen.blit(texte, (a-g,d))
            
            #fit
            fit=self.environment.drones[self.ind_curentDrone].fitness()
            fit=str(int(fit*1000)/1000)
           
            texte = police.render("fit : "+fit,True,(255, 0, 0))
            k,l=texte.get_size()
            self.screen.blit(texte, (a-g,d+h))
            
            P=[]
            for position in self.environment.drones[self.ind_curentDrone].history["position"]:
                P.append(self.offset_Point(position.x_scal(self.zoom)))
            if(len(P)>2):
                pygame.draw.lines(self.screen, (25,255,25), False, P,1)
            
            histo_speed=self.environment.drones[self.ind_curentDrone].history["speed"]
            histo_fit=self.environment.drones[self.ind_curentDrone].history["fitness"]
            histo_cap=self.environment.drones[self.ind_curentDrone].history["cap"]
            if(len(histo_speed)>60):
                histo_speed=histo_speed[-60:]
                histo_fit=histo_fit[-60:]
                histo_cap=histo_cap[-60:]
            if(len(histo_speed)>2):
                max_speed=max([abs(speed) for speed in histo_speed])
                max_fit=max([abs(fit) for fit in histo_fit])
            else:
                max_speed=1
                max_fit=1
            if max_speed==0:
                max_speed=1

            P=[]
            Q=[]
            R=[]
            for i,speed in enumerate(histo_speed):
                P.append((c+i*(a-c)/60, b-(b-d+f)/2-speed/max_speed*(b-d)/3))
                Q.append((c+i*(a-c)/60, b-(b-d+f)/2-histo_fit[i]/max_fit*(b-d)/3))
                R.append((c+i*(a-c)/60, b-(b-d+f)/2-histo_cap[i]/(3.141592)*(b-d)/3))
                
            pygame.draw.lines(self.screen, (200,100,205), False, [(c, b-(b-d+f)/2), (a, b-(b-d+f)/2)],1)
            
            if(2<len(P)<60):
                pygame.draw.lines(self.screen, (0,255,25), False, P,1)
                pygame.draw.lines(self.screen, (255,0,0), False, Q,1)
                pygame.draw.lines(self.screen, (0,50,100), False, R,1)
            elif(len(P)>=60):
                pygame.draw.lines(self.screen, (0,255,25), False, P[-60:],1)
                pygame.draw.lines(self.screen, (255,0,0), False, Q[-60:],1)
                pygame.draw.lines(self.screen, (0,50,100), False, R[-60:],1)

    
    def run(self):
        t1=t0=time.time() #save time
        T=[]
        while(not self.eventDisplay.stop):
            self.size=self.screen.get_size() #reupdate size
            self.clock.tick(60)
            #time.sleep(max(1/30-time.time()-t0,0))
            dt=time.time()-t1
            t1=time.time()
            self.eventDisplay.setDt(dt)
            print("Display dt :", dt)
            if(not self.eventDisplay.pause):
                self.time+=self.eventDisplay.dt*self.eventDisplay.coefTime
                self.eventDisplay.simulation=True
                self.eventDisplay.radar=True
                self.eventDisplay.communication=True

            
            self.update_screen() #modifie la fenètre
            pygame.display.flip() #update

            
            
            if(len(T)>100):
                self.fps=1/statistics.mean(T)
                self.stdFps=statistics.stdev([1/e for e in T])
                T=[]
            T.append(self.eventDisplay.dt)
            
            for event in pygame.event.get(): #pécho les events
                self.process_event(event) #travail event
        
    def stop(self):
        self.eventDisplay.stop=True
        pygame.quit()  


class EventDisplay():
    def __init__(self):
        #communication entre la fenetre et la simulation
        self.pause=False ##sert a mettre en pause la simulation
        self.stop=False #stop la simulation et la fenètre
        
        self.dt=0  #temps reel 
        self.coefTime=1   #ralentissement de la simulation
        self.simulation=False
        self.radar=False
        self.communication=False

        self.lenListStepTime=1000
        self.listStepTime=[1/30 for i in range(self.lenListStepTime)]
        self.i_listStepTime=0
        
    def setDt(self, dt:float):
        self.listStepTime[self.i_listStepTime]=dt
        self.i_listStepTime+=1
        
        if self.i_listStepTime>=self.lenListStepTime:
            self.i_listStepTime=0
        
        self.dt=statistics.mean(self.listStepTime)


        
        
        