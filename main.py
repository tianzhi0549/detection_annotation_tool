# -*- coding: utf8 -*- 
import cv2, os, sys
import numpy as np

WIN_NAME="Image"

class Model:
    def __init__(self, root_path):
        self.im_filenames=sorted([_ for _ in os.listdir(root_path) if os.path.splitext(_)[1].lower()==".jpg"])
        self.root_path=root_path
        self.cur_img_index=-1
        self.scale=1
        self.shortest_side=650
        self.pad=20
        self.im_size=None # (h, w)

    def next_img_gt(self):
        try:
            self.cur_img_index+=1
            return self.img_gt(self.cur_img_index)
        except IndexError:
            self.cur_img_index-=1
            raise

    def prev_img_gt(self):
        try:
            self.cur_img_index-=1
            return self.img_gt(self.cur_img_index)
        except IndexError:
            self.cur_img_index+=1
            raise

    def img_gt(self, index):
        if index<0:
            raise IndexError()
        print "当前图像: %s(%d/%d)"%(self.im_filenames[index], index+1, len(self.im_filenames))
        im=cv2.imread(os.path.join(self.root_path, self.im_filenames[index]))
        self.scale=self.shortest_side/float(min(*im.shape[:2]))
        self.im_size=im.shape[:2]
        im_resized=cv2.resize(im, (0, 0), fx=self.scale, fy=self.scale)
        im_padded=cv2.copyMakeBorder(im_resized, self.pad, self.pad, self.pad, self.pad, cv2.BORDER_CONSTANT, value=(128, 128, 128))
        return im_padded, self.get_polygon_list(index)

    def get_first_unlabeled_img(self):
        for index, im_filename in enumerate(self.im_filenames):
            if not self.exist_gt(im_filename):
                self.cur_img_index=index
                return self.img_gt(index)
        raise IndexError()

    def get_polygon_list(self, index):
        im_filename=self.im_filenames[index]
        if not self.exist_gt(im_filename):
            return []
        gt_filename=self.im_name_to_gt_name(im_filename)
        gt_file=os.path.join(self.root_path, gt_filename)
        return self.read_gt(gt_file)

    def exist_gt(self, im_filename):
        gt_filename=self.im_name_to_gt_name(im_filename)
        return os.path.exists(os.path.join(self.root_path, gt_filename))

    def save(self, gts):
        gt_filename=self.im_name_to_gt_name(self.im_filenames[self.cur_img_index])
        self.write_gt(os.path.join(self.root_path, gt_filename), gts)

    def read_gt(self, gt_file):
        polygon_list=[]
        fp=open(gt_file)
        for line in fp:
            line=line.strip()
            if line!="":
                polygon_list.append([self.transform_coord(int(_)) for _ in line.split()])
        fp.close()
        return polygon_list

    def transform_coord(self, coord):
        return int(coord*self.scale+self.pad)

    def restore_coord(self, polygon, index):
        coord=max(0, int((polygon[index]-self.pad)/self.scale))
        if index%2==0: # x
            return min(coord, self.im_size[1])
        else:
            return min(coord, self.im_size[0])

    def write_gt(self, gt_file, polygon_list):
        fp=open(gt_file, "w")
        for polygon in polygon_list:
            fp.write("%s\n"%" ".join([str(self.restore_coord(polygon, _)) for _ in range(len(polygon))]))
        fp.close()


    def im_name_to_gt_name(self, im_name):
        return os.path.splitext(im_name)[0]+".txt"

class Controller:
    def __init__(self, model):
        self.model=model
        try:
            self.img, self.gts=self.model.get_first_unlabeled_img()
        except IndexError:
            try:
                self.img, self.gts=self.model.next_img_gt()
            except IndexError:
                print "没有找到任何图像。"

        self.cur_state=1 # 0 create mode, 1 finished mode

    def key_event_handler(self, key):
        if key==119 or key==115: # W S
            if len(self.gts)!=0:
                self.model.save(self.gts)
            try:
                if key==115:
                    self.img, self.gts=self.model.next_img_gt()
                else:
                    self.img, self.gts=self.model.prev_img_gt()
            except IndexError:
                print "没有更多了:-)."
            self.cur_state=1
        elif key==68: # D
            self.model.save(self.gts)
        elif key==117: # U
            self.undo()
        elif key==27:
            exit(0)

    def mouse_event_handler(self, event, x, y):
        if event==cv2.EVENT_LBUTTONUP:
            if self.cur_state==1:
                self.gts.append([x, y])
                self.cur_state=0
            else:
                self.gts[-1].extend([x, y])
        elif event==cv2.EVENT_RBUTTONUP:
            self.cur_state=1

    def undo(self):
        if self.cur_state==0:
            if len(self.gts[-1])==2:
                del self.gts[-1]
                self.cur_state=1
            else:
                del self.gts[-1][-2:]
        else:
            if len(self.gts)!=0:
                self.cur_state=0

    def show_img(self):
        img_buf=self.img.copy()
        for poly in self.gts:
            points=zip(poly[::2], poly[1::2])
            cv2.polylines(img_buf, np.int32([points]), self.cur_state if poly is self.gts[-1] else True, (0, 0, 255))
            for p in points:
                cv2.circle(img_buf, p, 1, (255, 0, 0), thickness=5)
        cv2.imshow(WIN_NAME, img_buf)

def mouse_event_handler(event,x,y,flags,param):
        controller.mouse_event_handler(event, x, y)

if __name__=="__main__":
    if len(sys.argv)<2:
        print "用法: python main.py 图片文件夹路径"
        exit(-1)
    model=Model(sys.argv[1])
    controller=Controller(model)
    cv2.namedWindow(WIN_NAME)
    cv2.setMouseCallback(WIN_NAME, mouse_event_handler)
    while True:
        controller.show_img()
        controller.key_event_handler(cv2.waitKey(1)&0xFF)

