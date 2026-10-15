
  it('counts the file, not the list, when a second file shares one name with the first (DEC-1117 B1)', async () => {
    const { container } = renderShopping([ALPHA]);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    // jsdom's File has no text(), so the test gives it one.
    const pick = (body: string) => {
      const file = new File([body], 'owned.txt', { type: 'text/plain' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
    };
    const hint = 'To replace the list, use Clear owned first.';

    pick('Sol Ring\n2x Arcane Signet\n');
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(
      `Added 2 unique cards (3 total). 3 cards loaded. ${hint}`,
    ));

    // Arcane Signet is loaded already; Swords to Plowshares is new. The file
    // holds 2 unique cards; the list then holds 3 unique cards and 5 cards.
    pick('Arcane Signet\nSwords to Plowshares\n');
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(
      `Added 2 unique cards (2 total). 5 cards loaded. ${hint}`,
    ));
    expect(screen.getByText('5 cards loaded — saved locally')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toEqual(
      [['Sol Ring', 1], ['Arcane Signet', 3], ['Swords to Plowshares', 1]],
    );
  });
