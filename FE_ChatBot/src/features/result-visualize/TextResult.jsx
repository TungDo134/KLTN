function TextResult({ data }) {
  return (
    <div className="text-neutral-200 leading-relaxed">
      <ul className="list-disc ml-6 mt-2">
        {data.map((item, index) => (
          <li>
            {item.day}: {item.title} - {item.description}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TextResult;
