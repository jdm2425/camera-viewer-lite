# import bessel_optimisation
# print("Starting step 1 out of 3.")
# beam = bessel_optimisation.bessel(webcam_index=0)
# beam.plot_initial()
# print("Starting step 2 out of 3.")
# beam.decompose(no_roots = 20, max_order = 20, display = False)
# print("Starting step 3 out of 3.")
# beam.metric()
# beam.plot_reconstructed()
# print(beam.metric())
# print("Finished!")


import spot_optimisation
beam = spot_optimisation.spot(webcam_index=0, plot=False)#,preimage="C:\\Users\\Timur\\Pictures\\spottest1.png")
print(beam.metric())
