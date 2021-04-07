
import torch 
import models 
import logging 
import argparse 
import torch.optim as optim
import torch.nn.functional as F

from tools import Tools
from tqdm import trange,tqdm 
from trainer import Trainer
from models.gcn import GCN 
from dataset import Dataset
from sklearn.metrics import accuracy_score as accuracy
from algorithms.label_propagation import LabelPropagation

class Agent:
    def __init__(self):
        self.cfg=self.config()
        self.logger=Tools.get_logger(__name__)
        self.logger.info("Label Rate:%s"%self.cfg.label_rate)
        self.data_set=Dataset(self.cfg).load_dataset()
        if self.cfg.data_set=='mnist10k':
            adj,feature,labels,N,M=self.data_set
            self.idx_confuse=Dataset.entropy_adj(adj,labels[:int(self.cfg.label_rate*len(labels))],labels)
            
        else:
            adj, features, labels, idx_train, idx_val, idx_test=self.data_set
        if self.cfg.cuda:
            self.adj=adj.cuda()
        else:
            self.adj=adj
            self.labels=labels
        '''
        self.model = GCN(nfeat=features.shape[1],
                nhid=self.cfg.hidden,
                nclass=labels.max().item() + 1,
                dropout=self.cfg.dropout)
        if self.cfg.cuda:
            self.model.cuda()
            self.features = features.cuda()
            self.adj = adj.cuda()
            self.labels = labels.cuda()
            self.idx_train = idx_train.cuda()
            self.idx_val = idx_val.cuda()
            self.idx_test = idx_test.cuda()
        # Model and optimizer
        self.optimizer = optim.Adam(self.model.parameters(),lr=self.cfg.lr, weight_decay=self.cfg.weight_decay)
        '''
    def config(self):
        parser = argparse.ArgumentParser(description='uncertainty')
        
        parser.add_argument('--baselines',default=['lgc','gcn'])
        parser.add_argument('--dropout', type=float, default=0.5)
        parser.add_argument('--model',default='gcn')
        parser.add_argument('--hidden',type=int,default=16)
        parser.add_argument('--weight_decay', type=float, default=5e-4)
        parser.add_argument('--dataset_path',default='data/MNIST10k.mat')
        parser.add_argument('--data_set',default='mnist10k')
        parser.add_argument('--label_rate',default=0.02,type=float)
        parser.add_argument('--num_knn',default=10)
        parser.add_argument('--train_batch_size',default=128)
        parser.add_argument('--epochs',default=200)
        parser.add_argument('--lr',default=0.02)
        parser.add_argument('--cuda',default=False)
        return parser.parse_args()
    def train(self):
        self.model.train()
        self.optimizer.zero_grad()
        output = self.model(self.features, self.adj)
        loss_train = F.nll_loss(output[self.idx_train], self.labels[self.idx_train])
        acc_train = self.evaluate(output[self.idx_train], self.labels[self.idx_train])
        loss_train.backward()
        self.optimizer.step()
        loss_val = F.nll_loss(output[self.idx_val], self.labels[self.idx_val])
        acc_val= self.evaluate(output[self.idx_val], self.labels[self.idx_val])
        self.logger.info("loss_train {:.4f}, acc_train{:.4f}, loss_val:{:.4f}, acc_val:{:.4f}".format(loss_train.item(),acc_train.item(),loss_val.item(),acc_val.item() ))
    def test(self):
        self.model.eval()
        output = self.model(self.features, self.adj)
        loss_test = F.nll_loss(output[self.idx_test], self.labels[self.idx_test])
        acc_test = self.evaluate(output[self.idx_test], self.labels[self.idx_test])
        self.logger.info("loss {:.4f}, accuracy{:.4f}".format(loss_test.item(),acc_test.item() ))

    def run(self):
        for baseline in self.cfg.baselines:
            if baseline=='lgc':
                output=LabelPropagation.lgc(self.adj,self.labels,len(self.labels),int(len(self.labels)*self.cfg.label_rate),10,self.logger)
                accuracy=accuracy(output,self.labels)
                confuse_accuracy=accuracy(output[self.idx_confuse],self.labels[self.idx_confuse])
                self.logger.info("confuse_accurady%s,accuracy%s"%(confuse_accuracy,accuracy6))
                self.logger.info("---------------------------")
            if baseline=='gcn':
                self.cfg.model='gcn'
                trainer=Trainer(self.cfg)
                trainer.train()

if __name__=='__main__':
    agent=Agent()
    agent.run()