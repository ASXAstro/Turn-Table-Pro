Turn Table Pro: Professional Viewport Sync & Rotation

Turn Table Pro is a high-performance utility for Blender artists to inspect models across multiple viewports simultaneously with professional-grade rotation modes and intelligent pivot control.

Key Features

Classic Turntable: Smooth, 360-degree constant rotation for silhouette evaluation and presentation.

Micro Sweep: Controlled back-and-forth oscillation designed to track lighting response and specular highlights across surfaces.

Inspect Mode: Dynamic rotation with subtle speed variation to help reveal surface irregularities, topology artifacts, and mesh pinching.

Smart Pivot: Automatically centers rotation on Edit Mode selections, Object origins, or the 3D Cursor depending on context.

Viewport Navigation Cast: A streamlined Cast and Receive system that synchronizes viewport navigation across multiple Blender windows.

Real-time Mirroring: Replicates camera angle, zoom, pan, and focal length across connected viewports in real time.

Professional Turntable Engines

Stop manually orbiting your model. Turn Table Pro provides three specialized rotation engines designed for different inspection workflows:

Turntable: The industry standard for presentation and silhouette validation with constant-speed rotation.

Sweep: Oscillates across a controlled angle range—ideal for detecting sculpting artifacts, surface tension, and lighting behavior.

Inspect: Introduces subtle, natural speed variation to simulate a manual inspection orbit, making topology issues easier to detect.

Smart Pivot Logic

The add-on prevents camera drift by intelligently calculating the most relevant center of rotation.

Edit Mode: Automatically pivots around the Median Point of selected vertices. If nothing is selected, it defaults to the Object Origin.

Object Mode: Uses the 3D Cursor as the rotation center when no active selection is present, ensuring consistent and predictable navigation.

Viewport Navigation Cast

The updated Navigation Cast system introduces a simplified and optimized Cast and Receive architecture for synchronizing viewport movement across multiple Blender windows.

Cast System: One viewport acts as the Caster, broadcasting its navigation data.

Receive Mode: Any viewport with Receive enabled follows the Caster’s movement precisely.

Full Navigation Sync: Rotation, pan, zoom, and focal length are mirrored in real time across all receiving viewports.

This redesigned system replaces the older Peer Mirror method with a clearer and more efficient workflow, making multi-viewport synchronization easier to understand and more reliable in practice.

Interactive Monitoring

Navigation Cast remains active even when turntable rotation is disabled. You can manually navigate in the Caster viewport while all Receiver viewports follow the exact movement instantly.

This enables precise side-by-side inspection of multiple scenes or separate blend files while maintaining identical camera position and viewing angle across every viewport. It is particularly useful for asset comparison, shader validation, and detailed model inspection workflows where consistent viewing alignment is critical.
