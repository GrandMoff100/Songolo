FROM gitpod/workspace-full

# Install Dependencies
RUN yes | sudo apt-get install ffmpeg
RUN python -m pip install poetry
RUN python -m poetry env use system
RUN python -m poetry update
RUN python -m poetry install
