from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, LerpScaleInterval, Wait
from panda3d.core import Point3, TextNode, AmbientLight, DirectionalLight, LVector3, TransparencyAttrib
from direct.task import Task
import random, sys

class GalaxyDefender(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        # Game state
        self.game_started = False
        self.game_over = False
        self.score = 0
        self.health = 100
        self.keys = {}
        self.bullets = []
        self.enemies = []
        self.stars = []

        # Camera
        self.camera.setPos(0, -18, 6)
        self.camera.lookAt(0, 0, 0)

        # Lighting (brighter for clarity)
        self.setup_lights()

        # HUD & screens
        self.title_text = OnscreenText(text="GALAXY DEFENDER", pos=(0, 0.3), scale=0.12, align=TextNode.ACenter)
        self.start_text = OnscreenText(text="Press ENTER to Start", pos=(0, 0.1), scale=0.07, align=TextNode.ACenter)
        self.hint_text = OnscreenText(text="W A S D - Move • Space - Shoot • Esc - Quit", pos=(0, -0.95), scale=0.045, align=TextNode.ACenter)
        self.score_text = OnscreenText(text="Score: 0", pos=(-1.25, 0.92), scale=0.06, align=TextNode.ALeft)
        self.health_text = OnscreenText(text="Health: 100", pos=(0.9, 0.92), scale=0.06, align=TextNode.ALeft)
        self.gameover_text = OnscreenText(text="", pos=(0, 0.15), scale=0.09, fg=(1,0.2,0.2,1), align=TextNode.ACenter)
        self.restart_text = OnscreenText(text="", pos=(0, -0.05), scale=0.06, align=TextNode.ACenter)

        # Build simple scene objects (player + initial enemies not visible until start)
        self.create_player()
        self.create_starfield()

        # Accept keys
        self.accept("enter", self.start_game)
        self.accept("escape", sys.exit)
        self.accept("r", self.try_restart)
        # key down/up
        for k in ["w","a","s","d","space"]:
            self.accept(k, self.set_key, [k, True])
            self.accept(f"{k}-up", self.set_key, [k, False])

        # Tasks
        self.taskMgr.add(self.update, "update")

    # ---------- Setup helpers ----------
    def setup_lights(self):
        al = AmbientLight('ambient')
        al.setColor((0.9, 0.9, 0.9, 1))
        dl = DirectionalLight('dir')
        dl.setColor((1,1,1,1))
        dl.setDirection(LVector3(0, 8, -2))
        self.render.setLight(self.render.attachNewNode(al))
        self.render.setLight(self.render.attachNewNode(dl))

    def create_player(self):
        # Use built-in cube model so no external file required
        self.player = self.loader.loadModel("models/misc/rgbCube")
        self.player.setScale(0.45, 0.6, 0.25)
        self.player.setColor(0, 1, 0, 1)
        self.player.setPos(0, 0, 0)
        self.player.reparentTo(self.render)

    def spawn_enemies(self, count=6):
        # Clear old enemies
        for e in self.enemies:
            try: e.removeNode()
            except: pass
        self.enemies = []
        for i in range(count):
            e = self.loader.loadModel("models/misc/rgbCube")
            e.setScale(0.35)
            # vivid colors for contrast
            e.setColor(random.choice([(1,0,0,1),(1,1,0,1),(1,0,1,1)]))
            e.setPos(random.uniform(-6,6), random.uniform(12,30), random.uniform(-2,2))
            e.reparentTo(self.render)
            self.enemies.append(e)

    def create_starfield(self, n=120):
        # small cubes as stars (very small, subtle)
        for i in range(n):
            s = self.loader.loadModel("models/misc/rgbCube")
            scale = random.uniform(0.03, 0.08)
            s.setScale(scale)
            s.setPos(random.uniform(-25,25), random.uniform(-10,50), random.uniform(-6,6))
            # bright white-ish or bluish stars
            c = random.choice([(1,1,1,1),(0.8,0.9,1,1),(0.9,0.9,0.8,1)])
            s.setColor(*c)
            s.setTransparency(TransparencyAttrib.MAlpha)
            s.reparentTo(self.render)
            self.stars.append((s, random.uniform(0.02, 0.08)))  # (node, speed)

    # ---------- Input ----------
    def set_key(self, key, value):
        self.keys[key] = value

    def start_game(self):
        if self.game_started and not self.game_over:
            return
        # initialize/reset game variables
        self.game_started = True
        self.game_over = False
        self.score = 0
        self.health = 100
        self.score_text.setText("Score: 0")
        self.health_text.setText("Health: 100")
        self.title_text.hide()
        self.start_text.hide()
        self.gameover_text.setText("")
        self.restart_text.setText("")
        self.spawn_enemies(8)

    def try_restart(self):
        if self.game_over:
            # remove bullets & enemies then restart
            for b in self.bullets:
                try: b.removeNode()
                except: pass
            self.bullets = []
            for e in self.enemies:
                try: e.removeNode()
                except: pass
            self.enemies = []
            self.start_game()

    # ---------- Visual effects ----------
    def create_muzzle_flash(self, pos):
        flash = self.loader.loadModel("models/misc/rgbCube")
        flash.reparentTo(self.render)
        flash.setPos(pos)
        flash.setScale(0.08)
        flash.setColor(1, 0.85, 0, 1)
        flash.setTransparency(TransparencyAttrib.MAlpha)
        # quick pop animation
        Sequence(
            LerpScaleInterval(flash, 0.08, (0.35,0.35,0.35)),
            LerpScaleInterval(flash, 0.08, (0.01,0.01,0.01)),
            Func(flash.removeNode)
        ).start()

    def create_explosion(self, pos):
        expl = self.loader.loadModel("models/misc/rgbCube")
        expl.reparentTo(self.render)
        expl.setPos(pos)
        expl.setScale(0.15)
        expl.setColor(1, 0.5, 0, 1)
        expl.setTransparency(TransparencyAttrib.MAlpha)
        # scale + fade
        Sequence(
            Parallel(
                LerpScaleInterval(expl, 0.25, (1.8,1.8,1.8)),
            ),
            Func(expl.removeNode)
        ).start()

    # ---------- Update loop ----------
    def update(self, task):
        dt = globalClock.getDt()

        # animate stars slowly toward camera to give movement feeling
        for s, speed in list(self.stars):
            s.setY(s, -speed * (dt*20))
            # recycle stars that pass behind camera
            if s.getY() < -12:
                s.setPos(random.uniform(-25,25), random.uniform(20,50), random.uniform(-6,6))

        # If game not started, keep early-screen animations only
        if not self.game_started:
            # subtle pulsing of title
            return Task.cont

        # If game over, freeze gameplay
        if self.game_over:
            return Task.cont

        # Player movement (smooth with key states)
        move_speed = 8 * dt
        pos = self.player.getPos()
        if self.keys.get("w"):
            pos += Point3(0, move_speed, 0)
        if self.keys.get("s"):
            pos += Point3(0, -move_speed, 0)
        if self.keys.get("a"):
            pos += Point3(-move_speed, 0, 0)
        if self.keys.get("d"):
            pos += Point3(move_speed, 0, 0)
        # clamp boundaries
        pos.setX(max(-8, min(8, pos.getX())))
        pos.setY(max(-6, min(18, pos.getY())))
        pos.setZ( max(-3, min(3, pos.getZ())) )
        self.player.setPos(pos)

        # Shooting (space registers as state; we spawn bullets when pressed)
        if self.keys.get("space"):
            # create bullet and muzzle flash, simple rate limit using last bullet time
            if not hasattr(self, "last_shot"):
                self.last_shot = 0
            if task.time - self.last_shot > 0.18:  # fire rate
                self.last_shot = task.time
                b = self.loader.loadModel("models/misc/rgbCube")
                b.reparentTo(self.render)
                b.setScale(0.09, 0.25, 0.09)
                b.setColor(1,1,0,1)
                b.setPos(self.player.getPos() + Point3(0, 1.0, 0))
                self.bullets.append(b)
                self.create_muzzle_flash(b.getPos())

        # Update bullets
        for b in list(self.bullets):
            b.setY(b, 40 * dt)
            if b.getY() > 60:
                try: b.removeNode()
                except: pass
                if b in self.bullets: self.bullets.remove(b)

        # Update enemies
        for e in list(self.enemies):
            # approach player
            e.setY(e, -1.6 * dt)
            # slight sideways wobble
            e.setX( e.getX() + 0.6 * dt * (random.random()-0.5) )

            # if enemy passes behind player (too close), damage player and reset enemy
            if e.getY() < -4:
                self.health -= 10
                self.health_text.setText(f"Health: {self.health}")
                # explosion visual
                self.create_explosion(e.getPos())
                # reposition enemy farther
                e.setPos(random.uniform(-6,6), random.uniform(12,30), random.uniform(-2,2))
                if self.health <= 0:
                    self.trigger_game_over()
                    break

            # bullet collisions
            for b in list(self.bullets):
                if (e.getPos() - b.getPos()).length() < 0.7:
                    # hit!
                    self.score += 10
                    self.score_text.setText(f"Score: {self.score}")
                    self.create_explosion(e.getPos())
                    try: b.removeNode()
                    except: pass
                    if b in self.bullets: self.bullets.remove(b)
                    # reset enemy
                    e.setPos(random.uniform(-6,6), random.uniform(16,36), random.uniform(-2,2))
                    break

        return Task.cont

    def trigger_game_over(self):
        self.game_over = True
        self.game_started = False
        self.gameover_text.setText("GAME OVER")
        self.restart_text.setText("Press R to Restart • Esc to Quit")
        # show final title again
        self.title_text.show()
        self.start_text.show()

# Run
if __name__ == "__main__":
    app = GalaxyDefender()
    app.run()
