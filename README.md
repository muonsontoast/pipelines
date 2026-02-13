# Pipelines
Pipelines is a EPICS-compatible node-based editor developed for offline and control room optimisation tasks at particle accelerator facilities. It excels as a useful tool in time-constrained scenarios where the user wants to try several tasks in a machine shift where they may only have a few hours of allocated time. Conversely, tasks involving dozens or more variables as is common in the likes of transfer line trajectory optimisation with multiple BPMs, can be organised and decluttered with the use of Groups.

## Key Features

- **Blocks**: every variable is displayed as a block in the editor that can be dragged, renamed, linked, and more.

- **Inspector**: scrutinise blocks in fine-detail and access additional attributes not shown in the editor.

- **Area select**: select multiple blocks at once and apply selection-wide changes from one place with 'Shift+Drag'.

- **Persistence**: session data is saved as a YAML file and easy to pass to other colleagues.

- **Groups**: group elements together with 'Ctrl+G' to declutter the editor, with an optional group name and note, for intelligibility at a glance.

- **Composition**: compose blocks by adding or multiplying them to achieve specific goals.

- **Safety**: pause, resume or stop running blocks from the editor, giving the user the final say.

## Getting Started

Load up Python or any venv and navigate to the repository root and install the necessary packages by running the command:
- **pip install -r requirements.txt**

Navigate up a level to the folder containing the repository and run it as a module with this command:
- **python -m pipelines \<optional lattice_name\>**

Place a PyAT .mat lattice file inside **/lattice-saves** before trying to launch the app with a lattice, mind!

## Configuring Your First Pipeline - A Transfer Line
The app has four main sections: *Editor*, *Inspector*, *Lattice Viewer*, *System Info*. The editor is the canvas upon which blocks and links are drawn; the inspector is the panel to the right that displays context-specific information on selected blocks in the editor; the lattice viewer displays a loaded lattice if one is provided; system info shows live information about the CPU, and GPU, RAM and disk utilisation.

### Process Variable Block
Right-click the editor and a pop-up menu will appear. In the search bar, type 'PV' and select the matching item in the dropdown. Next to the name in the menu appears a shortcut for performing the operation (Shift+P). Many actions in the app have similar shortcuts, and you are encouraged to learn them. Hurrah, a PV block should have appeared adjacent to the menu. Select the newly placed block and the inspector will display additional information including its name, values, and any linked elements. Place a second PV in the editor with the menu or shortcut and move it close to the first.

### Optimiser Block
Place a Single Task GP block into the editor either by searching in the popup menu or with the shortcut 'Shift+G'. Drag the block to be somewhat to the right of the two PVs. There are many configurable options on the block and you are encouraged to play with them. For this first task, leave it on its default values.

### Kernel Block
Kernels define the class of functions that can be learned by a Gaussian Process. For this first task, add a Radial Basis Function (RBF) kernel to the editor by searching in the popup menu. This is a defacto choice for optimisation tasks where the objective function is believed to be smooth.

### Linking everything up
Most blocks have sockets. If they appear on the left of a block, they receive links and are an ingoing socket, and if they appear on the right, links extend from them and they are an outgoing socket. A link is formed by hovering over an outgoing socket, pressing, dragging to another ingoing socket, and releasing. If a link is valid as determined by the blocks themselves, it will be permanently added to the editor. Create a link between one of the PVs and the *decision* socket of the optimiser. Link the other PV to the *objective* socket. Finally, link the kernel to the *kernel* socket. At this point, the optimiser is configured and ready to go. To run it, here is what needs to happen next:

### Offline
If a lattice is not already loaded, close the app to save the session settings, place a PyAT .mat lattice file into the */lattice-saves* folder and relaunch the app passing the lattice name (without .mat) as an additional argument in the CLI. If successful, a lattice should appear in the viewer. If not, check for misspelling. Now select the decision PV and link it with a corrector in the lattice using the *Linked Lattice Element* component of the inspector. Make sure to press 'Enter' to confirm your choice or it won't apply. Link the objective PV to a BPM in the lattice in the same way. Hit *Start* on the optimiser and the block should begin to run.

### Online
Select the decision PV and change its name to match a real corrector PV in the machine. Once a match is detected, real-time values should appear in the set and get windows below the block. Link the objective PV to a real BPM in the same way and you should see live values below its block too. Hit *Start* on the optimiser and the block should begin to run.

After the block has finished running, a dataset will appear in the */datadump* folder timestamped with the time when it was first launched, which should match what is shown by the block. 

Congratulations on making it this far and I hope I have managed to demonstrate the utility of the tool for the control room. There are many more features to discover and I encourage you to do so. Here are some more things that are worth looking into: kernel composition, PV composition, and optimiser constraints.
