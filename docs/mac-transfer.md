# Transfer to the MacBook Pro

Git transfers source and documentation. It does not transfer this chat's
execution host, the Windows virtual environment, ignored music, or outputs.

1. Open a terminal on the MacBook and clone:

   ```sh
   git clone https://github.com/ericbfriday/StackChanDancer.git
   cd StackChanDancer
   ```

2. Follow the macOS setup in the README; use Python 3.13 with the committed
   `uv.lock` for the closest dependency match to Windows.
3. Transfer your audio separately (AirDrop or another private device route).
   Do not add it to the public repository.
4. Open this checkout in the local Codex app. Use this continuation prompt:

   > Continue StackChanDancer on this Mac. Read README.md and the docs, install
   > the locked Python environment, run the Python and JavaScript tests, then
   > build and validate a dance from my local audio. Do not flash a robot yet.

5. Run a local build, then work through the board calibration/integration
   sequence in `docs/architecture.md` when hardware is available.
