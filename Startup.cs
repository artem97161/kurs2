using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Data.Sqlite;
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Linq;
using Microsoft.AspNetCore.Mvc;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();

var app = builder.Build();

app.UseRouting();
app.UseEndpoints(endpoints => {
    endpoints.MapControllers();
});

app.Run();

public class Place
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string Category { get; set; }
    public string Address { get; set; }
}

public class GeoApiResponse
{
    public List<Feature> features { get; set; }
}

public class Feature
{
    public Properties properties { get; set; }
}

public class Properties
{
    public string name { get; set; }
    public List<string> categories { get; set; }
    public string address_line2 { get; set; }
}

public class AddressResponse
{
    public List<AddressFeature> features { get; set; }
}

public class AddressFeature
{
    public AddressProperties properties { get; set; }
}

public class AddressProperties
{
    public string formatted { get; set; }
}

[ApiController]
[Route("places")]
public class PlacesController : ControllerBase
{
    private readonly string _connectionString = "Data Source=places.db";

    public PlacesController()
    {
        CreateDatabase();
        UpdateDatabase();
    }

    private void CreateDatabase()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = @"
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                category TEXT,
                address TEXT
            );
        ";
        command.ExecuteNonQuery();
    }

    private void UpdateDatabase()
    {
        var places = GetCityPlaces("all");

        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var deleteCommand = connection.CreateCommand();
        deleteCommand.CommandText = "DELETE FROM places";
        deleteCommand.ExecuteNonQuery();

        foreach (var place in places)
        {
            var insertCommand = connection.CreateCommand();
            insertCommand.CommandText = @"
                INSERT INTO places (name, category, address)
                VALUES ($name, $category, $address);
            ";
            insertCommand.Parameters.AddWithValue("$name", place.Name);
            insertCommand.Parameters.AddWithValue("$category", place.Category);
            insertCommand.Parameters.AddWithValue("$address", place.Address);
            insertCommand.ExecuteNonQuery();
        }

        PrintDatabaseContent(); // добавленная строка
    }

    private void PrintDatabaseContent()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM places";
        using var reader = command.ExecuteReader();
        Console.WriteLine("Содержимое базы данных:");
        while (reader.Read())
        {
            Console.WriteLine($"Id: {reader.GetInt32(0)}, Name: {reader.GetString(1)}, Category: {reader.GetString(2)}, Address: {reader.GetString(3)}");
        }
    }


    private List<Place> GetCityPlaces(string category)
    {
        try
        {
            var apiKey = "c91ab8f84d2a42e985f6989c202900bb";
            var latitude = "50.4501";
            var longitude = "30.5234";
            var radius = 1000;

            using var client = new HttpClient();
            var url = $"https://api.geoapify.com/v2/places?categories={category}&filter=circle:{longitude},{latitude},{radius}&apiKey={apiKey}";
            Console.WriteLine(url);
            HttpResponseMessage response = client.GetAsync(url).Result;

            if (response.IsSuccessStatusCode)
            {
                var placesJson = response.Content.ReadAsStringAsync().Result;
                var placesData = JsonSerializer.Deserialize<GeoApiResponse>(placesJson);

                if (placesData != null && placesData.features != null)
                {
                    return placesData.features.Select(place => new Place
                    {
                        Name = place.properties.name,
                        Category = string.Join(", ", place.properties.categories),
                        Address = place.properties.address_line2
                    }).ToList();
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error fetching city places: {ex.Message}");
        }

        return new List<Place>();
    }
    [HttpGet("list_all_places")]
    public IActionResult ListAllPlaces()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM places";
        using var reader = command.ExecuteReader();
        var places = new List<Place>();
        while (reader.Read())
        {
            places.Add(new Place
            {
                Id = reader.GetInt32(0),
                Name = reader.GetString(1),
                Category = reader.GetString(2),
                Address = reader.GetString(3)
            });
        }
        if (places.Any())
        {
            return Ok(places);
        }
        return NotFound(new { error = "База данных пуста." });
    }

    [HttpPost("add_place")]
    public IActionResult AddPlace([FromBody] Place place)
    {
        try
        {
            using var connection = new SqliteConnection(_connectionString);
            connection.Open();
            var command = connection.CreateCommand();
            command.CommandText = @"
                INSERT INTO places (name, category, address)
                VALUES ($name, $category, $address);
            ";
            command.Parameters.AddWithValue("$name", place.Name);
            command.Parameters.AddWithValue("$category", place.Category);
            command.Parameters.AddWithValue("$address", place.Address);
            command.ExecuteNonQuery();
            return Created("", new { message = "Место успешно добавлено!" });
        }
        catch (Exception e)
        {
            return BadRequest(new { error = e.Message });
        }
    }

    [HttpGet("place_by_name/{name}")]
    public IActionResult GetPlaceByName(string name)
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT address FROM places WHERE name = $name";
        command.Parameters.AddWithValue("$name", name);
        using var reader = command.ExecuteReader();
        if (reader.Read())
        {
            return Ok(new { address = reader.GetString(0) });
        }
        return NotFound(new { error = "Place not found" });
    }

    [HttpGet("place_by_address/{address}")]
    public IActionResult GetPlaceByAddress(string address)
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT name FROM places WHERE address = $address";
        command.Parameters.AddWithValue("$address", address);
        using var reader = command.ExecuteReader();
        if (reader.Read())
        {
            return Ok(new { name = reader.GetString(0) });
        }
        return NotFound(new { error = "Place not found" });
    }

    [HttpGet("list_places/{category}")]
    public IActionResult ListPlaces(string category)
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM places WHERE category LIKE $category";
        command.Parameters.AddWithValue("$category", "%" + category + "%");
        using var reader = command.ExecuteReader();
        var places = new List<Place>();
        while (reader.Read())
        {
            places.Add(new Place
            {
                Id = reader.GetInt32(0),
                Name = reader.GetString(1),
                Category = reader.GetString(2),
                Address = reader.GetString(3)
            });
        }
        if (places.Count > 0)
        {
            return Ok(places);
        }
        return NotFound(new { error = "No places found for this category" });
    }

    [HttpPut("update_place/{name}")]
    public IActionResult UpdatePlace(string name, [FromBody] Place place)
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "UPDATE places SET address = $address WHERE name = $name";
        command.Parameters.AddWithValue("$address", place.Address);
        command.Parameters.AddWithValue("$name", name);
        var rowsAffected = command.ExecuteNonQuery();
        if (rowsAffected > 0)
        {
            return Ok(new { message = $"Place '{name}' updated successfully" });
        }
        return NotFound(new { error = "Place not found" });
    }

    [HttpDelete("delete_place/{name}")]
    public IActionResult DeletePlace(string name)
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        var command = connection.CreateCommand();
        command.CommandText = "DELETE FROM places WHERE name = $name";
        command.Parameters.AddWithValue("$name", name);
        var rowsAffected = command.ExecuteNonQuery();
        if (rowsAffected > 0)
        {
            return Ok(new { message = $"Place '{name}' deleted successfully" });
        }
        return NotFound(new { error = "Place not found" });
    }
}
