class inventoryAllocator(object):
    ''' 
    This is the inventory class
    Methods:
    isInventoryOver - checks if all products in inventory are finished
    Variables:
    inventory - This holds the current product stock information (including the initial values)
    '''

    inventory = {'A':150,'B':150,'C':100,'D':100,'E':200}

    def __init__(self,name): # name just gives a name to this class
        self.name = name
    def isInventoryOver(self):
        result = [x==0 for x in self.inventory.values()]
        return reduce(lambda x,y: x and y,result)


class order(inventoryAllocator):
    ''' 
    This is the order class which is derived from parent class 'inventoryAllocator'
    Methods:
    readOrders - This method reads the orders from a data source, in our case, it is file whose path can be provided
    processOrderStatement - This method converts the initial order statement to a simplified one containing only the dictionary representation of product and its vale
                            It removes unnecessary keywords like "Product", "Quantity" etc
    simplifyOrderSt - This method converts a list of product orders to a dict of the same for easy processing e.g.[{A:1,C:1}] to {A:1,C:1}                        
    processOrderAgainstInventory - This method is called for each input order and allocates it as per the following rules
                        1) Inbound orders to the allocator should be individually identifyable (ie two streams may generate orders with an identical header, but these orders should be identifyable from their streams)
                        2) Inventory should be allocated on a first come, first served basis; once allocated, inventory is not available to any other order.
                        3) Inventory should never drop below 0.
                        4) If a line cannot be satisfied, it should not be allocated.  Rather, it should be  backordered (but other lines on the same order may still be satisfied).
                        5) When all inventory is zero, the system should halt and produce output listing, in the order received by the system, the header of each order, the quantity on each line, the quantity allocated to each line, and the quantity backordered for each line.
    
    check_inventory - This method finds the product request and checks if it can be satisfied - it is called as part of processOrderAgainstInventory() method
    processMasksPerOrder - This method prepares the order mask, availability mask and the reordering mask
    createMasksPerOrder - This method makes a list of masks
    createOrderMask - This method creates the order mask based on product order e.g. {A:1,C:1} creates mask 1,0,1,0,0
    writeOrderHistory - This method outputs the results in the following format to the file whose path is provided
    
  1: 1,0,1,0,0::1,0,1,0,0::0,0,0,0,0
  2: 0,0,0,0,5::0,0,0,0,0::0,0,0,0,5
  3: 0,0,0,4,0::0,0,0,0,0::0,0,0,4,0
  4: 1,0,1,0,0::1,0,0,0,0::0,0,1,0,0
  5: 0,3,0,0,0::0,3,0,0,0::0,0,0,0,0

    Variables:
    orders - This holds the list of all orders (in simplified form)
    inputPath - Path for input file where orders are placed
    outputPath - Path for output file where results in above format are stored
    masksPerOrder - This variable stores the 3 masks per order as a list
    stringsForOutputFile - This variable stores the output results in string format for easy writing to the file
    '''

    def __init__(self,name,inputPath,outputPath):
        self.name = name
        self.orders = []
        self.inputPath = inputPath
        self.outputPath = outputPath
        self.masksPerOrder = []
        
        
        self.stringsForOutputFile = ""
        self.headerStream = []
        self.currHeaderStream = 0
    
    def processOrderStatement(self,order_st):

        header_stream = order_st.split(',',1)[0]+'}' # Splitting out the Header identifier for order stream
        self.headerStream.append(header_stream.split(':',1)[1].rsplit('}',1)[0].strip())
        order_st = '{'+order_st.split(',',1)[1]

        orders = order_st.split(':',1) # Splitting out the product order
        orders1 = orders[1].rsplit('}',1)
        only_order_st = '['+orders1[0].strip()+']'+orders1[1].strip()
        only_order_st = only_order_st.strip()
        one_order_st_dict = {}
        one_order_st_dict["Lines"] = only_order_st

        Ndict = self.simplifyOrderSt(**one_order_st_dict) # Remove unneeded keywords like "Product", "Quantity"

        one_order_st_dict = {}
        one_order_st_dict["Lines"] = [Ndict]
        return one_order_st_dict

    def readOrders(self):
        f = open(self.inputPath)
        for line in f.readlines():
            order_st = line.strip()
            just_the_order_st = self.processOrderStatement(order_st)
            self.orders.append(just_the_order_st)

        f.close()

    def simplifyOrderSt(self, **singleProductOrder):
        Ndict = {}
        Nndict = {}
        for d in eval(singleProductOrder["Lines"]):
            Nndict = dict(map(None, *[iter(d.values())]*2))
            Ndict.update(Nndict)

        return Ndict

    def check_inventory(self,**singleProductOrderD):
        oMask = self.createOrderMask(**singleProductOrderD)
        availMask = oMask[:]
        for k,v in singleProductOrderD.items():
            if super(order,self).isInventoryOver() == True:
                print "No more Inventory, HALT"
                return False
            for k_i,v_i in super(order,self).inventory.items():
                #print k,v,k_i,v_i
                if k == k_i:
                    try:
                        result = int(v) <= 5 and int(v) > 0
                        #print int(v),result 
                        if result == False:
                            raise ValueError
                    except ValueError:
                        print ("Only extract more than 0 or less than 5")
                        continue
                    if int(int(v_i) - int(singleProductOrderD[k])) >= 0:
                        super(order,self).inventory[k]=int(int(v_i) - int(singleProductOrderD[k]))
                        print ("Inventory satisfies the request")
                    else:
                        oKeys = singleProductOrderD.keys()
                        Pos = [ord(char) - 64 for char in oKeys]
                        for pos in Pos:
                            if k == pos:
                                break
                        availMask[pos-1]=0
                        print ("Inventory does not satisfy the request, backordering")
                    break
        def xor(a,b):return int(a)^int(b)
        bkodrMask = map(xor,oMask,availMask)

        self.masksPerOrder = self.createMasksPerOrder(oMask,availMask,bkodrMask)
        return True

    def processOrderAgainstInventory(self):
        productOrderD = {}
        #stringsForOutputFile = ""
        for orderLocal,hdrStr in zip(self.orders,self.headerStream):
            self.currHeaderStream = hdrStr
            for item in orderLocal.values():
                if item == [{}]:
                    print "Invalid order, needs to have at least one product"
                    continue
                productOrderD["Lines"]=item 
            productOrderD = reduce(lambda r, d: r.update(d) or r, item, {}) #converts list to dict
            if self.check_inventory(**productOrderD) == False:
                return False
            self.processMasksPerOrder()
            productOrderD.clear()

    def processMasksPerOrder(self):
        masksForOutputFilePerOrder =[]
        for masks in self.masksPerOrder:
            mask = ','.join(masks)
            masksForOutputFilePerOrder.append(mask)
        stringForOutputFile = '::'.join(masksForOutputFilePerOrder)
        stringForOutputFile = self.currHeaderStream+":"+stringForOutputFile+"\n"

        self.stringsForOutputFile += stringForOutputFile


    def createMasksPerOrder(self,oMask,availMask,bkodrMask):
        masksPerOrder = []
        masksPerOrder.append(map(str,oMask))
        masksPerOrder.append(map(str,availMask))
        masksPerOrder.append(map(str,bkodrMask))
        return masksPerOrder

    def createOrderMask(self,**singleProductOrderD):
        oMask = []
        oKeys = singleProductOrderD.keys()
        oValues = singleProductOrderD.values()
        Pos = [ord(char) - 64 for char in oKeys]
        oMask=[0,0,0,0,0]
        oValueIdx =0
        for idx in range(len(oMask)):
            for pos in Pos:
                if idx+1 == pos:
                    oMask[idx] |= 1
                    oMask[idx] *= oValues[oValueIdx] 
                    oValueIdx += 1
                continue
        return oMask

    def writeOrderHistory(self):        
        f = open(self.outputPath,"w+")
        f.writelines(self.stringsForOutputFile)
        f.writelines('\n')
        f.close()
    
IA = inventoryAllocator("Test") # Create the inventory allocator object
OD = order("TestOrder",'C:\Python\orders.txt','C:\Python\ordersHist.txt') #Create the product order object with parms
OD.readOrders() #Call the readOrders method
status = OD.processOrderAgainstInventory() #Process the orders against inventory
if status == False: # If no more inventory, HALT the system
    print "Halting the system as inventory Over"
OD.writeOrderHistory() #Print the results in output file
print "Final Inventory Status", IA.inventory.items()
