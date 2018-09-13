from tosca import app


if __name__ == '__main__':
    context = ('server.pem', 'server.key')
    app.run(host="0.0.0.0", port=8879, debug=False)
