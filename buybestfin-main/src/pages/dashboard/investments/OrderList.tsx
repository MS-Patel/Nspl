import OrderListComponent from '@/components/investments/OrderList';

const OrderList = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Order History</h2>
      </div>
      <OrderListComponent />
    </div>
  );
};

export default OrderList;
