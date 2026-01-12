An app inspired by UI from the game design industry, hopefully accelerating research in the field of particle accelerator optimisation. Drag and drop Process Variable (PV) building blocks, multiple ML models including Single and Multi-task Gaussian Processes (GPs), Variational auto-encoders (VAEs), Reinforcement Learning (RL) agents, and perform standard accelerator operations like Orbit Response Measurements (ORMs), all in one visual interactive editor. Open multiple editors at once to work with several such pipelines in one go. PVs can simultaneously define elements in a real machine as well as be linked to virtual elements inside a model. This allows you to directly compare model to machine, and gives your ML model components access to both real and virtual data pools concurrently. Query the lattice for different elements with the inspector. Filter by element type, and instantly get information on location, index, and class-specific information. Interfaces with BoTorch, GPyTorch and Xopt under-the-hood.

Keep in mind this is a nice tool designed for rapid ideation and testing with real particle accelerators and offline models. It is NOT a lattice / model designer.

A very early example of what you can do with the tool:

<img width="2096" height="1192" alt="Screenshot 2026-01-11 222512" src="https://github.com/user-attachments/assets/98f2d898-0229-44c5-9a1e-26106020a086" />
**Caption**: _Live Setup on the Diamond Light Source accelerator. Real-time PV values are being streamed with aioca. In the figure, a single objective BO loop is being performed with the sum of BPM charges along a transfer line the objective to maximise. The objective is filtered through a control block that halts the signal if a separate beam position PV exceeds some user-defined threshold, which the optimiser sees as a poor result. 6 steerer magnets are supplied as decision variables for this task. The result is dumped into a save folder and timestamped.
_
<img width="1889" height="1136" alt="image" src="https://github.com/user-attachments/assets/ab7d5048-fc1f-451b-ae40-b99f9899cd1f" />

<img width="955" height="715" alt="image" src="https://github.com/user-attachments/assets/18b27bb2-fa8b-4fcc-93af-4d40a675dbb5" />
**Caption**: _Earliest example of the pipelines editor GUI with PVs connected up to an orbit response block, run in a physics engine simulator (PyAT)._
