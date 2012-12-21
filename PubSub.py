class PubSub(object):
    """ A publisher/subscriber object used as a means of keeping coupling loose. """
    def __init__(self):
        self.handlers = {}

    def on(self, event, fun, infinite=True, repeats=0):
        """ Adds a subscriber function to this object. The function will be called
            at least once when the event occures, regardless of the repears parameter.

            Argument Details:
            event -- the event name, a string
            fun -- the callback function to call when the event is emitted
            infinite -- if true, callback function will always be called
            repeats -- the number of times to repeat the function call

        """
        if not event in self.handlers:
            self.handlers[event] = []
            
        wrapper = FunctionWrapper(fun, infinite, repeats)
        
        self.handlers[event].append(wrapper)

    def once(self, event, fun):
        """ Use when an event listener or subscriber only needs to be fired once.

            Argument Details:
            event -- the event name, a string
            fun -- the callback function to call when the event is emitted

        """
        self.on(event, fun, False)

    def emit(self, event, args=[]):
        """ Use to signal that an event has occured.


            Argument Details:
            event -- the event name, a string
            args -- variable arguments to pass to the callbacks of this event
        """
        if event in self.handlers:
            for wrapper in self.handlers[event]:
                wrapper.call(self, event, *args)
            self.handlers[event] = [x for x in self.handlers[event] if not x.finished]

class FunctionWrapper(object):
    """ An inner class used by the PubSub class to
        wrap subscriber functions, and limit their use."""
    def __init__(self, fun, infinite, repeats):
        self.fun = fun
        self.infinite = infinite
        self.repeats = repeats
        self.count = 0

        self.finished = False

    def call(self, emitter, event, *args):
        self.fun(emitter, event, args)

        self.count = self.count + 1
        if not self.infinite and self.count > self.repeats:
            self.finished = True
            


if __name__ == '__main__':
    ps = PubSub()

    # In Python 2.x, print is a statement.
    # Lambda's need expressions, so I wrapped the print statement in a function.
    def printAsFunction(emitter, event, args):
        print emitter, 'was told to', event, ''.join([' '.join(args), '.'])
        
    ps.once('say', lambda emitter, event, args: printAsFunction(emitter, event, args or ["nothing"]))
    
    ps.emit('say', ['hello'])
    ps.emit('say', ['hello'])

    ps.on('say', lambda emitter, event, args: printAsFunction(emitter, event, args or ["nothing"]), False, 3)
    ps.emit('say') # no args
    ps.emit('say', ['hello'])
    
    ps.emit('Something you are not prepared for')
    ps.emit('Something you are not prepared for', ['with arguments'])

