from gpiozero import Button, LED
import time
import Config as cfg

half_button = Button(cfg.half_press_index, hold_time=0.05)
full_button = Button(cfg.full_press_index, hold_time=0.05)
laser = LED(cfg.laser_index)

def standard_mode(bot, c, loser_mode=False):
    """ Half press trigger to lock on and track. Full press to fire """
    bot.trigger(force_off=True)

    # Wait for button to be released if it started being held
    while half_button.is_held or full_button.is_held:
        if cfg.DEBUG_MODE:
            print('BUTTON HELD AT START OF NEW MODE LOOP')
            time.sleep(0.1)
        pass

    laser.on()

    # Wait unti half press is first triggered
    while not half_button.is_held:
        if cfg.DEBUG_MODE:
            print('WAITING FOR TRIGGER HALF PRESS')
            time.sleep(0.1)
        pass

    # Start tracking center frame
    c.lock_on()
    bot.reset_pid()

    if cfg.DEBUG_MODE:
        print('LOCKING ON')

    w_center_pix, h_center_pix = cfg.laser_center
    loser_loop = False
    normal_loop = False
    lock_on_time = time.time()

    # Stay in this tracking until trigger is released or shot is fired
    while half_button.is_held:
        h, w = c.get_location()
        
        pid_mult = (time.time() - lock_on_time) / cfg.aim_lock_fade_s
        pid_mult = pid_mult if pid_mult < cfg.aim_lock_fade_s else cfg.aim_lock_fade_s
        print(pid_mult)

        if h != 0 and w != 0 and loser_loop == False and normal_loop == False:
            pitch_pid, yaw_pid = bot.update_target(h - h_center_pix, w_center_pix - w, pid_mult)  # Yes this is correct, deal wit it
        elif h != 0 and w != 0 and loser_loop == True:
            pitch_pid, yaw_pid = bot.update_target(h - h_center_pix, w_center_pix - w - cfg.loser_mode_bump_pixels)
        elif h != 0 and w != 0 and normal_loop == True:
            pitch_pid, yaw_pid = bot.update_target(h - h_center_pix - cfg.normal_mode_vertical_bump, w_center_pix - w - cfg.normal_mode_horiz_bump)
        else:
            bot.reset_pid()  # Reset control loops on tracking error to avoid jump on re-acquisition
            lock_on_time = time.time()

        if full_button.is_held:
            laser.off()
            if cfg.DEBUG_MODE:
                print('Pulling Trigger')
                
            if bot.trigger() == True:
                break

            # It's fine don't look at this
            if loser_mode:
                loser_loop = True
                if cfg.DEBUG_MODE:
                    print('Executing Loser Mode')
            else:
                normal_loop = True

    bot.trigger(force_off=True)
    laser.off()
    

def face_mode(bot, c):
    """ Will aim and fire at first face it sees as long as trigger is held """
    bot.trigger(force_off=True)

    # Wait for button to be released if it started being held
    while half_button.is_pressed or full_button.is_pressed:
        if cfg.DEBUG_MODE:
            print('BUTTON HELD AT START OF NEW MODE LOOP')
            time.sleep(0.2)
        pass

    laser.on()

    # Wait unti half press is first triggered
    half_button.wait_for_press()
    while not full_button.is_pressed:
        if cfg.DEBUG_MODE:
            print('WAITING FOR TRIGGER FULL PRESS')
            time.sleep(0.2)
        pass

    w_center_pix, h_center_pix = cfg.laser_center

    while full_button.is_pressed:
        face_location = c.find_face()

        if face_location is None:
            continue

        c.lock_on(face_location)
        bot.reset_pid()
        if cfg.DEBUG_MODE:
            print('FACE locked on')

        while full_button.is_pressed:
            h, w = c.get_location()
            if h != 0 and w != 0:
                pitch_pid, yaw_pid = bot.update_target(h - h_center_pix + cfg.normal_mode_vertical_bump, w_center_pix - w + cfg.normal_mode_horiz_bump)
                if cfg.DEBUG_MODE:
                    print('PID: {}, {}'.format(pitch_pid, yaw_pid))

            if abs(h - h_center_pix) < cfg.face_mode_close_enough_pixels and abs(w - w_center_pix) < cfg.face_mode_close_enough_pixels:
                if cfg.DEBUG_MODE:
                    print('Pulling Trigger')
                if bot.trigger() == True:
                    break

    bot.trigger(force_off=True)
    laser.off()
