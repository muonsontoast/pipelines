Pipelines is a visual node-based editor designed for rapid testing of optimisation ideas in the control rooms of particle accelerator facilities. Drag and drop blocks inside the editor and connect them up to form simple or complex pipelines to achieve a range of optimisation objectives. Exploit your knowledge of the physics of a system by composing kernels to improve sample efficiency and converge sooner. Filters introduce control logic that can halt or permit the flow of information along pipelines. Every actionable block can be paused, resumed and reset at any time to offer the final say on safety to the user. Modify the name of PV blocks to match those in a machine to automatically stream values of real variables. Alternatively, create a .mat lattice file in PyAT (Python Accelerator Toolbox) and link PVs to elements and perform optimisation on a lattice, or fuse simulation with reality.

Pipelines is currently being built atop the EPICS library and aioca to interface with Diamond Light Source Process Variables (PVs), though many other facilities use EPICS and the intention is to role it out over time. 

To get setup, download the github repo and install the required packages by running the following command:

pip install -r requirements.txt

Navigate to the folder where the repo is located (not inside of it) and run the following command:

python -m pipelines (optional lattice file)

<img width="2096" height="1192" alt="Screenshot 2026-01-11 222512" src="https://github.com/user-attachments/assets/98f2d898-0229-44c5-9a1e-26106020a086" />
Caption: Live setup on the Diamond Light Source accelerator. Real-time EPICS PVs are being streamed with aioca. In the figure, a single objective BO loop is being performed with the sum of BPM charges along a transfer line the objective to maximise. The objective is filtered through a control block that halts the signal if a separate beam position PV exceeds some user-defined threshold, which the optimiser sees as a poor result. 6 steerer magnets are supplied as decision variables for this task. The result is dumped into a save folder and timestamped.
<br>
<img width="2551" height="1478" alt="image" src="https://github.com/user-attachments/assets/c9082ff6-c79d-44d3-bb2b-59615ce92bf2" />
<br>
<img width="955" height="715" alt="image" src="https://github.com/user-attachments/assets/18b27bb2-fa8b-4fcc-93af-4d40a675dbb5" />
Caption: Earliest example of the pipelines editor GUI with PVs connected up to an orbit response block, run in a physics engine simulator (PyAT).
