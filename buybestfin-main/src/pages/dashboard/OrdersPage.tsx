import OrderList from '@/components/investments/OrderList';

const OrdersPage = () => {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Order Management</h1>
        <p className="text-muted-foreground">Track and manage your investment orders.</p>
      </div>
      <OrderList />
    </div>
  );
};

export default OrdersPage;
