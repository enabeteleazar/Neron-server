import SystemMetricCard from "./SystemMetricCard";

const SystemOverview = ({ data }) => {
  return (
    <div className="system-overview">
      <SystemMetricCard label="CPU" value={`${data.cpu.percent}%`} />
      <SystemMetricCard label="RAM" value={`${data.ram.percent}%`} />
      <SystemMetricCard label="Load" value={data.load.load1} />
      <SystemMetricCard label="Disque" value={`${data.disk.percent}%`} />
      <SystemMetricCard
        label="Réseau"
        value={`RX ${data.network.rx} / TX ${data.network.tx}`}
      />
    </div>
  );
};

export default SystemOverview;
