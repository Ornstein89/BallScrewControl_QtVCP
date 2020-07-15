import hal, time
h = hal.component("passthrough")
h.newpin("siggen.0.sine", hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("out", hal.HAL_FLOAT, hal.HAL_OUT)
h.ready()

if(not hal.component_exists("siggen")):
    print("*** NEGATIVE hal.component_exists(\"siggen\")")
else:
    print("***POSITIVE hal.component_exists(\"siggen\")")

try:
    while 1:
        time.sleep(1)
        h['out'] = h['in']
except KeyboardInterrupt:
    raise SystemExit