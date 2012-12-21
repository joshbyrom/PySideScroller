import pygame

from PubSub import *
from GameEngine import *

class SpriteSheet(PubSub):
    def __init__(self, filepath):
        PubSub.__init__(self)
        
        self.filepath = filepath
        self.surface = pygame.image.load(filepath)

        self.reels = {}

    def add_reel(self, name, reel):
        self.reels[name] = reel
        self.emit('reel added', [name, reel])

    def get_reel(self, name):
        return self.reels[name]

    def get_active_reels(self):
        return [x for x in self.reels if x.active]


class Reel(PubSub):
    def __init__(self, direction = 'horizontal'):
        PubSub.__init__(self)
        self.direction = direction
        
        self.rects = []

    def load(self, offset, size, frames):
        for index in xrange(frames):
            x, y = self._determine_position(offset, size, index)
            self.rects.append((x, y, size[0], size[1]))

        self.emit('loaded')

    def _determine_position(self, offset, size, index):
        x = offset[0]
        y = offset[1]

        if self.direction == 'horizontal':
            x += size[0] * index
        else:
            y += size[1] * index

        return x, y

class AnimationController(PubSub):
    def __init__(self, spritesheet, name):
        PubSub.__init__(self)
        
        self.spritesheet = spritesheet
        self.name = name
        self.reel = spritesheet.get_reel(name)

        self.position = (0, 0)

        self.active = False
        self.current = 0
        self.last = len(self.reel.rects)
        self.frame_duration = 0

        self.count = 0
        self.repeats = 0

        self.time_since_last_frame_change = 0
        
    def start(self, frame_duration, repeats = 0):
        self.current = 0
        self.frame_duration = frame_duration
        self.resume()

        self.time_since_last_frame_change = 0
        self.count = 0
        self.repeats = repeats
        self.emit('started')

    def stop(self):
        self.active = False
        self.emit('stopped')

    def resume(self):
        self.active = True

    def update(self, elapsed):
        if not self.active or self.count > self.repeats:
            return

        if self.time_since_last_frame_change >= self.frame_duration:
            self.current = (self.current + 1) % self.last
            if self.current < 0:
                self.current += self.last
            self.time_since_last_frame_change = 0

            if self.current == (self.last - 1):
                self.count += 1

                if self.count > self.repeats:
                    self.stop()
                    self.emit('finished')

        self.time_since_last_frame_change += elapsed

    def get_current_surface(self):
        rect = self.reel.rects[self.current]
        surface = self.spritesheet.surface.subsurface(rect)
        return surface
            

class AnimationSequence(PubSub):
    def __init__(self, spritesheet):
        PubSub.__init__(self)
        
        self.spritesheet = spritesheet
        
        self.animation_controllers = []
        self.start_args = []

        self.active = False
        self.current = 0

    def add_animation(self, name, duration, count):
        controller = AnimationController(self.spritesheet, name)
        controller.once('finished', self.handle_controller_finished)
        
        self.animation_controllers.append(controller)
        self.start_args.append((duration, count))

    def start(self):
        if self.current != 0:
            self.get_current_controller().stop()

        self.current = -1
        self.next_animation()
        
        self.active = True

    def update(self, elapsed):
        if not self.active:
            return
        
        self.get_current_controller().update(elapsed)

    def handle_controller_finished(self, controller, event, *args):
        self.emit('change')
        self.next_animation()

    def next_animation(self):
        self.current = self.current + 1

        if self.current < len(self.animation_controllers):
            controller = self.get_current_controller()
            duration, count = self.start_args[self.current]
            
            controller.start(duration, count)
        else:
            self.active = False
            self.emit('finished')

    def get_current_controller(self):
        return self.animation_controllers[self.current]
                       
                                          
class SpriteSheetView(PubSub):
    def __init__(self, spritesheet):
        PubSub.__init__(self)

        self.spritesheet = spritesheet
        self.spritesheet.on('reel added', self.handle_reel)
        self.position = (0, 0)
        
        self.animation_sequence = None
        self.animation_controllers = []
        self.update_hooked = False

    def handle_reel(self, spritesheet, event, args):
        name, reel = args
        controller = AnimationController(self.spritesheet, name)
        self.animation_controllers.append(controller)
        
    def render(self, engine, event, args):
        surface = args[0]
        self.hook_animation_loop(engine)

        if self.animation_sequence:
            self.render_controller(
                self.animation_sequence.get_current_controller(),
                surface
            )

        for controller in self.animation_controllers:
            self.render_controller(controller, surface)

    def render_controller(self, controller, surface):
        if controller.active:
            position = [self.position[x] + controller.position[x]
                            for x in xrange(len(self.position))]

            c_surface = controller.get_current_surface()
            surface.blit(c_surface, (position[0],
                                     position[1],
                                     c_surface.get_width(),
                                     c_surface.get_height()))

    def play_sequence(self, sequence):
        self.animation_sequence = sequence
        self.animation_sequence.once('finished', self.handle_sequence_finished)
        
        self.animation_sequence.start()

    def handle_sequence_finished(self, emitter, event, *args):
        self.animation_sequence = None
        self.emit('sequence finished')

    def hook_animation_loop(self, engine):
        if not self.update_hooked:
            engine.on('tick', self.update)
            self.update_hooked = True
            

    def update(self, engine, event, args):
        elapsed = args[0]
        if self.animation_sequence:
            self.animation_sequence.update(elapsed)
            
        for controller in self.animation_controllers:
            controller.update(elapsed)


    def start_animation(self, name, duration, repeats = 0):
        return len([x.start(duration, repeats)
                    for x in self.animation_controllers
                        if x.name == name])

    def stop_animation(self, name):
        return len([x.stop()
                    for x in self.animation_controllers
                        if x.name == name])

    def get_animation_controller(self, name):
        return [x for x in self.animation_controllers if x.name == name]
            
if __name__ == '__main__':
    import os
    import sys

    filepath = os.path.join(sys.path[0], 'mon3_sprite_base.png')

    def on_init(engine, event, *args):
        sheet = SpriteSheet(filepath)
        view = SpriteSheetView(sheet)
        
        idle = Reel()
        idle.load((0, 0), (64, 64), 5)
        sheet.add_reel('idle', idle)

        atk = Reel()
        atk.load((0, 64), (64, 64), 5)
        sheet.add_reel('attack', atk)

        hurt = Reel()
        hurt.load((0, 128), (64, 64), 3)
        sheet.add_reel('hurt', hurt)

        dead = Reel()
        dead.load((0, 128), (64, 64), 7)
        sheet.add_reel('dead', dead)

        animation_sequence = AnimationSequence(sheet)
        animation_sequence.add_animation('idle', 200, 3)
        animation_sequence.add_animation('hurt', 100, 2)
        animation_sequence.add_animation('idle', 50, 5)
        animation_sequence.add_animation('attack', 50, 2)
        animation_sequence.add_animation('hurt', 100, 2)
        animation_sequence.add_animation('dead', 100, 0)

        view.play_sequence(animation_sequence)
        engine.on('render', view.render)

        
    engine = Engine()
    engine.on('init', on_init)
    engine.set_caption('SpriteSheet Unit Test')
    engine.start()
