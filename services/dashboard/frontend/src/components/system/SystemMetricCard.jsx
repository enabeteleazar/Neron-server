const SystemMetricCard = ({ label, value }) => (
  <div className="metric-card">
    <span className="metric-label">{label}</span>
    <span className="metric-value">{value}</span>
  </div>
);

export default SystemMetricCard;
