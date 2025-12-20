const Section = ({ title, children }) => (
  <section className="dashboard-section">
    <h2>{title}</h2>
    {children}
  </section>
);

export default Section;
