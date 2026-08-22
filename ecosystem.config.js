module.exports = {
  apps: [
    {
      name: "openforge-api",
      script: "D:\\AI-Tools\\Python\\python.exe",
      args: "-m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000",
      cwd: "C:\\Users\\Hugop\\opensource-staging\\openforge\\v1-starter",
      autorestart: true,
      max_restarts: 20,
    },
  ],
};
