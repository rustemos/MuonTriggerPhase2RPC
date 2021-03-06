
import pandas as pd
import numpy as np
import os
import sys
import pprint
import logging

import torch
import torch.nn as nn
import matplotlib.pyplot as plt

from optparse import OptionParser

p = OptionParser()

p.add_option('--nepoch', '-n',          type='int',   default= 3000)

p.add_option('--input-dim',             type='int',   default= 3)
p.add_option('--output-dim',            type='int',   default= 1)
p.add_option('--fc1',                   type='int',   default=20)
p.add_option('--fc2',                   type='int',   default=20)
p.add_option('--fc3',                   type='int',   default=20)

p.add_option('--learning-rate1',        type='float', default=0.001)
p.add_option('--learning-rate2',        type='float', default=0.0001)
p.add_option('--learning-rate3',        type='float', default=0.00001)

p.add_option('--mse',             action = 'store_true', default = False, help='use square error loss function')
p.add_option('--l1e',             action = 'store_true', default = False, help='use linear error loss function')
p.add_option('--sme',             action = 'store_true', default = False, help='use smooth linear error loss function')

p.add_option('--show-net',        action = 'store_true', default = False, help='show network')
p.add_option('-d', '--debug',     action = 'store_true', default = False, help='print debug info')
p.add_option('-p', '--plot',      action = 'store_true', default = False, help='plot histograms')

(options, args) = p.parse_args()

#----------------------------------------------------------------------------------------------    
def getFilePath(suffix=None):

    if len(args) != 1:
        info('main - missing input data path: {}'.format(args))
        return

    fpath = args[0]

    if fpath.count('.csv') != 1:
        info('main - input file must end with .csv: {}'.format(fpath))
        sys.exit(0)

    if suffix == None:
        if not os.path.isfile(fpath):
            info('main - missing input data path: {}'.format(fpath))
            sys.exit(0)

        return fpath

    fbase = os.path.dirname(fpath)

    if fbase and len(fbase) > 1 and not os.path.isdir(fbase):
        raise Exception('getFilePath - invalid directory="{}" - this should never happen'.format(fbase))

    return fpath.replace('.csv', suffix)

#----------------------------------------------------------------------------------------------
def getLog(name, level='INFO', debug=False, print_time=False, verbose=False):

    if print_time:
        f = logging.Formatter('%(asctime)s - %(name)s: %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    elif options.debug:
        f = logging.Formatter('%(name)s: %(levelname)s - %(message)s')
    else:
        f = logging.Formatter('%(message)s')

    ff = logging.Formatter('%(asctime)s: %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    fh = logging.FileHandler(filename=getFilePath('_train.log'))
    fh.setFormatter(f)
    fh.setFormatter(ff)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(f)

    log = logging.getLogger(name)
    log.addHandler(fh)
    log.addHandler(sh)

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        if level == 'DEBUG':   log.setLevel(logging.DEBUG)
        if level == 'INFO':    log.setLevel(logging.INFO)
        if level == 'WARNING': log.setLevel(logging.WARNING)
        if level == 'ERROR':   log.setLevel(logging.ERROR)

    return log

#----------------------------------------------------------------------------------------------
log = getLog(os.path.basename(__file__), debug=options.debug)

#----------------------------------------------------------------------------------------------
def info(*args):

    out = ''

    for arg in args:
        out += '{} '.format(arg)

    log.info(out)

#----------------------------------------------------------------------------------------------    
def waitForClick(figs = []):

    if not options.plot:
        return

    info('Click on figure to continue, close to exit programme...')

    while True:
        try:
            result = plt.waitforbuttonpress()
        except:
            info('waitForClick - exiting programme on canvas close')
            sys.exit(0)

        if result == False:
            break

    for f in figs:
        plt.close(f)

#----------------------------------------------------------------------------------------------    
def prepareData(datapath):

    event = pd.read_csv(datapath, header = None)

    trainDr = (event.values[:,0:3])
    trainTr =  event.values[:,3:4]

    info('train data:   mean={}, std={}'.format(trainDr.mean(axis=0), trainDr.std(axis=0)))
    info('train target: mean={}, std={}'.format(trainTr.mean(axis=0), trainTr.std(axis=0)))

    info(trainDr)
    info(trainTr)

    trainD = trainDr.astype(np.float32)
    trainT = trainTr.astype(np.float32)

    trainDm = torch.from_numpy(trainD)
    trainTm = torch.from_numpy(trainT)

    info('trainDr shape:', trainDr.shape)
    info('trainDm shape:', trainDm.shape)
    info('trainTr shape:', trainTr.shape)
    info('trainTm shape:', trainTm.shape)

    return [trainDm, trainTm]

#----------------------------------------------------------------------------------------------    
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.fc1 = nn.Linear(options.input_dim, options.fc1)
        self.fc2 = nn.Linear(options.fc1, options.fc2)
        self.fc3 = nn.Linear(options.fc2, options.fc3)
        self.fc4 = nn.Linear(options.fc3, options.output_dim)

    def forward(self,x):
        x = nn.functional.relu(self.fc1(x))
        x = nn.functional.relu(self.fc2(x))
        x = nn.functional.relu(self.fc3(x))
        x = self.fc4(x)
        return x

#----------------------------------------------------------------------------------------------    
def learnReg(net, nepoch, learningRate, trainDm, trainTm, currStep):

    if options.mse:
        loss_func = nn.MSELoss(reduction='mean')
    elif options.sme:
        loss_func = nn.SmoothL1Loss()
    else:
        loss_func = nn.L1Loss()

    optimizer = torch.optim.SGD(net.parameters(), lr = learningRate, momentum=0.9)

    TotalLoss = np.zeros((options.nepoch))

    for epo in range(nepoch):
        prediction = net(trainDm)
        loss = loss_func(prediction, trainTm)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        info('Epoch [{}/{}], Loss: {:.4f}'.format(epo+1, nepoch, loss.data.numpy()))
        TotalLoss[epo] = loss.data.numpy()

    pred = net(trainDm).detach().numpy()
    info(pred)

    f1 = plt.figure()
    plt.scatter(x = trainTm, y = pred, marker = 'o', s = 0.1)
    plt.xlabel('TrainData(1/Gev)')
    plt.ylabel('Prediction(1/Gev)')
    f1.show(False)
    plt.savefig(getFilePath('_epoch{:d}_TargetVsResult.png'.format(currStep)))

    f2 = plt.figure()
    plt.scatter(x = np.arange(0, options.nepoch), y = TotalLoss, s = 0.1)
    plt.xlabel('Epoch')
    plt.ylabel('Total loss')
    f2.show(False)
    plt.savefig(getFilePath('_epoch{:d}_LossVsEpoch.png'.format(currStep)))

    if options.show_net:
        log.info('TODO - implement code to visualize neural network')

    waitForClick([f1, f2])

#----------------------------------------------------------------------------------------------    
def main():

    info('args=', args)
    info('options=', options)

    net = Net()
    net.train()

    fpath = getFilePath()

    if not os.path.isfile(fpath):
        info('main - missing input data path: {}'.format(fpath))
        return

    if fpath.count('.csv') != 1:
        info('main - input file must end with .csv: {}'.format(fpath))
        return

    data = prepareData(fpath)

    learnReg(net, options.nepoch, options.learning_rate1, data[0], data[1], 1)
    learnReg(net, options.nepoch, options.learning_rate2, data[0], data[1], 2)
    learnReg(net, options.nepoch, options.learning_rate3, data[0], data[1], 3)

    info('Finished training, will save state dictionary:')
    info(pprint.pformat(net.state_dict()))

    torch.save(net.state_dict(), getFilePath('.pt'))

#------------------------------------------------------------------------------#
if __name__ == "__main__":
    main()